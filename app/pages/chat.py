import streamlit as st
import os
import sys
import time
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# load_dotenv()

# Add parent directory to path for importing utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from utils.embeddings import TextEmbeddings
from utils.rag import get_db
from utils.session_state import initialize_session_state
from utils.authentication import init_auth_session
import requests

# Page configuration
st.set_page_config(
    page_title="Multimodal RAG Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide default Streamlit page navigation
hide_pages_style = """
    <style>
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
"""
st.markdown(hide_pages_style, unsafe_allow_html=True)

# Initialize authentication and session state
init_auth_session()
initialize_session_state()

# Simplified authentication check - only check session state
if not st.session_state.get('authenticated', False) or not st.session_state.get('user_info'):
    st.error("🔒 Authentication required. Please login first.")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔑 Go to Login", type="primary", use_container_width=True, key="chat_login_btn"):
            st.switch_page("main.py")
    st.stop()

# Ensure consistent session ID based on user authentication
user_info = st.session_state.get('user_info', {})
user_id = user_info.get('user_id', 'unknown')
session_token = st.session_state.get('session_token', 'no-token')

# Use a hash of user_id and session_token for consistent session ID
import hashlib
consistent_session_id = hashlib.md5(f"{user_id}_{session_token}".encode()).hexdigest()[:12]
st.session_state['session-id'] = consistent_session_id


class RAGChatbot:
    """RAG-powered chatbot that uses ChromaDB for context-aware responses"""
    
    def __init__(self, database, embedding_function):
        self.database = database
        self.embedding_function = embedding_function
        self.conversation_history = []
        
    def retrieve_context(self, query: str, k: int = 5) -> List[str]:
        """Retrieve relevant context from the database using enhanced search"""
        if not self.database:
            return []
        
        try:
            # Use similarity search with score threshold
            results = self.database.similarity_search_with_score(query, k=k)
            
            # Filter results by relevance score (lower score = more similar)
            context_chunks = []
            for doc, score in results:
                # Only include documents with decent relevance (adjust threshold as needed)
                if score < 1.5:  # ChromaDB uses distance, so lower is better
                    context_chunks.append(doc.page_content)
            
            # If no good matches, try a broader search
            if not context_chunks:
                fallback_results = self.database.similarity_search(query, k=min(k, 3))
                context_chunks = [doc.page_content for doc in fallback_results]
            
            return context_chunks
        except Exception as e:
            st.error(f"Error retrieving context: {e}")
            return []
    
    def get_sources(self, query: str, k: int = 3) -> List[Dict]:
        """Get source information for retrieved documents"""
        if not self.database:
            return []
        
        try:
            results = self.database.similarity_search_with_score(query, k=k)
            sources = []
            for doc, score in results:
                source_info = {
                    'content': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    'metadata': doc.metadata,
                    'relevance_score': float(score)
                }
                sources.append(source_info)
            return sources
        except Exception as e:
            st.error(f"Error getting sources: {e}")
            return []
    
    def enhance_query(self, query: str) -> List[str]:
        """Generate additional search queries to improve context retrieval"""
        enhanced_queries = [query]  # Start with original query
        
        # Add some query variations for better retrieval
        query_lower = query.lower()
        
        # If it's a question, also search for declarative statements
        if query_lower.startswith(('what', 'how', 'why', 'when', 'where', 'who')):
            # Extract key terms from the question
            key_terms = query.split()[1:]  # Skip question word
            if key_terms:
                enhanced_queries.append(' '.join(key_terms))
        
        # Add keyword-based variations
        if 'explain' in query_lower or 'describe' in query_lower:
            topic = query_lower.replace('explain', '').replace('describe', '').strip()
            enhanced_queries.append(topic)
        
        return enhanced_queries

    def retrieve_enhanced_context(self, query: str, k: int = 5) -> List[str]:
        """Retrieve context using multiple query variations"""
        if not self.database:
            return []
        
        all_contexts = []
        enhanced_queries = self.enhance_query(query)
        
        for enhanced_query in enhanced_queries:
            contexts = self.retrieve_context(enhanced_query, k=k//len(enhanced_queries) + 1)
            all_contexts.extend(contexts)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_contexts = []
        for context in all_contexts:
            if context not in seen:
                seen.add(context)
                unique_contexts.append(context)
        
        return unique_contexts[:k]  # Limit to requested number

    def generate_response(self, query: str, context: List[str]) -> str:
        """Generate response using the LLM with retrieved context"""
        
        # Prepare the prompt with context
        context_text = "\n\n".join(context) if context else "No relevant context found."
        
        # Include conversation history for continuity
        conversation_context = ""
        if self.conversation_history:
            recent_history = self.conversation_history[-3:]  # Last 3 exchanges
            for exchange in recent_history:
                conversation_context += f"Human: {exchange['user']}\nAssistant: {exchange['bot']}\n\n"
        
        # Analyze query type for better prompting
        query_lower = query.lower()
        is_summary = any(word in query_lower for word in ['summarize', 'summary', 'overview', 'main points'])
        is_comparison = any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs'])
        is_factual = any(word in query_lower for word in ['what', 'when', 'where', 'who'])
        is_explanation = any(word in query_lower for word in ['how', 'why', 'explain'])
        
        # Customize instructions based on query type
        if is_summary:
            task_instruction = "Provide a comprehensive summary of the key points from the context."
        elif is_comparison:
            task_instruction = "Compare the different aspects mentioned in the context, highlighting similarities and differences."
        elif is_explanation:
            task_instruction = "Provide a detailed explanation based on the context, breaking down complex concepts if needed."
        else:
            task_instruction = "Answer the question directly using information from the context."

        prompt = f"""You are a helpful AI assistant that answers questions based on provided document context.

Previous conversation:
{conversation_context}

Context from documents:
{context_text}

Current question: {query}

Task: {task_instruction}

Instructions:
1. Base your answer primarily on the provided context
2. If the context is insufficient, clearly state what information is missing
3. Be accurate and cite specific details from the context when relevant
4. Structure your response clearly with bullet points or numbered lists when appropriate
5. If this relates to previous conversation, acknowledge the connection
6. Keep responses focused and informative

Answer:"""
        
        try:
            # Make request to the LLM API
            response = requests.post(
                url="https://aihub-vvitu.social/api/ollama-api/generate/",
                headers={'API-KEY': st.secrets.get('OLLAMA-API-KEY')},
                # headers={'API-KEY': os.getenv('OLLAMA-API-KEY')},
                json={
                    "model": "gpt-oss:20b",  # Using a text generation model
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 1000
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['response']
            else:
                return f"Error: Failed to get response from AI model (Status: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return "Error: Request timed out. Please try again."
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """Main chat function that orchestrates the RAG process"""
        
        # Step 1: Retrieve relevant context using enhanced search
        with st.spinner("🔍 Searching through your documents..."):
            context = self.retrieve_enhanced_context(user_message, k=7)  # Get more context for better responses
            sources = self.get_sources(user_message)
        
        # Step 2: Generate response
        with st.spinner("🤖 Generating response..."):
            bot_response = self.generate_response(user_message, context)
        
        # Step 3: Store conversation history
        self.conversation_history.append({
            'user': user_message,
            'bot': bot_response,
            'context_used': len(context),
            'timestamp': time.time()
        })
        
        return {
            'response': bot_response,
            'sources': sources,
            'context_chunks': len(context),
            'conversation_length': len(self.conversation_history)
        }


def display_chat_message(message: str, is_user: bool = True):
    """Display a chat message with proper styling"""
    if is_user:
        with st.chat_message("user", avatar="👤"):
            st.write(message)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(message)


def display_sources(sources: List[Dict], expanded: bool = False):
    """Display source information in an expandable section"""
    if not sources:
        return
        
    with st.expander(f"📚 Sources ({len(sources)} documents)", expanded=expanded):
        for i, source in enumerate(sources):
            st.write(f"**Source {i+1}:**")
            st.write(f"📄 Content: {source['content']}")
            
            if source['metadata']:
                metadata_str = ", ".join([f"{k}: {v}" for k, v in source['metadata'].items() if v])
                if metadata_str:
                    st.write(f"📋 Metadata: {metadata_str}")
            
            st.write(f"🎯 Relevance: {source['relevance_score']:.3f}")
            st.divider()


def chat_interface():
    """Main chat interface"""
    st.title("🤖 RAG Chatbot")
    st.markdown("Ask questions about your uploaded documents!")
    
    # Check if database exists
    if 'db' not in st.session_state or st.session_state['db'] is None:
        st.error("❌ No processed documents found!")
        st.info("👈 Please go back and upload some documents first.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔙 Go Back to Upload", type="primary", use_container_width=True, key="chat_go_back_upload_btn"):
                st.session_state['page'] = 'upload'
                st.rerun()
        return
    
    # Initialize chatbot
    if 'chatbot' not in st.session_state:
        embedding_fn = TextEmbeddings()
        st.session_state['chatbot'] = RAGChatbot(st.session_state['db'], embedding_fn)
    
    # Display processed files info in sidebar
    with st.sidebar:
        
        # Logout button
        if st.button("🚪 Logout", type="secondary", use_container_width=True, key="chat_sidebar_logout_btn"):
            # Logout user
            auth_manager = st.session_state.get('auth_manager')
            if auth_manager and 'session_token' in st.session_state:
                auth_manager.logout_user(st.session_state['session_token'])
            
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Redirect to login
            st.switch_page("main.py")
        
        st.divider()
        
        # User info section
        st.header("👤 User Info")
        user_info = st.session_state.get('user_info', {})
        st.write(f"**Email:** {user_info.get('email', 'Unknown')}")
        st.write(f"**Session:** {st.session_state.get('session-id', 'Unknown')}")
        
        st.divider()
        
        st.header("📊 Session Info")
        
        if 'processed' in st.session_state:
            st.write(f"**Processed Files:** {len(st.session_state['processed'])}")
            for file in st.session_state['processed']:
                st.write(f"• {file}")
        
        st.write(f"**Session ID:** `{st.session_state.get('session-id', 'Unknown')}`")
        
        # Chat statistics
        if hasattr(st.session_state.get('chatbot'), 'conversation_history'):
            chat_count = len(st.session_state['chatbot'].conversation_history)
            st.write(f"**Messages Exchanged:** {chat_count}")
        
        st.divider()
        
        # Navigation
        st.header("🧭 Navigation")
        
        if st.button("📁 Back to Upload", type="secondary", use_container_width=True, key="chat_sidebar_back_btn"):
            st.session_state['page'] = 'upload'
            st.rerun()
        
        st.divider()
        
        # Reset conversation button
        if st.button("🔄 Clear Chat History", use_container_width=True, key="chat_clear_history_btn"):
            if 'chatbot' in st.session_state:
                st.session_state['chatbot'].conversation_history = []
            if 'chat_history' in st.session_state:
                st.session_state['chat_history'] = []
            st.success("Chat history cleared!")
            st.rerun()
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        if st.session_state['chat_history']:
            for chat in st.session_state['chat_history']:
                display_chat_message(chat['user'], is_user=True)
                display_chat_message(chat['bot'], is_user=False)
                
                # Display sources if available
                if chat.get('sources'):
                    display_sources(chat['sources'])
                
                st.divider()
    
    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_message = st.text_input(
                "💬 Ask me anything about your documents...",
                placeholder="e.g., What are the main topics discussed in the documents?",
                key="chat_input"
            )
        
        with col2:
            send_button = st.form_submit_button("Send 🚀", use_container_width=True)
    
    # Process user input
    if send_button and user_message.strip():
        # Display user message immediately
        display_chat_message(user_message, is_user=True)
        
        # Get bot response
        chatbot = st.session_state['chatbot']
        result = chatbot.chat(user_message.strip())
        
        # Display bot response
        display_chat_message(result['response'], is_user=False)
        
        # Display sources
        if result['sources']:
            display_sources(result['sources'])
        
        # Add to chat history
        chat_entry = {
            'user': user_message.strip(),
            'bot': result['response'],
            'sources': result['sources'],
            'timestamp': time.time()
        }
        st.session_state['chat_history'].append(chat_entry)
        
        # Show some statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 Context Chunks", result['context_chunks'])
        with col2:
            st.metric("📚 Sources Found", len(result['sources']))
        with col3:
            st.metric("💬 Total Exchanges", result['conversation_length'])
        
        # Rerun to update the chat display
        st.rerun()
    
    # Example questions
    if not st.session_state['chat_history']:
        st.markdown("### 💡 Example Questions:")
        # Dynamic example questions based on processed files
        example_questions = []
        
        # Get processed file types to suggest relevant questions
        if 'processed' in st.session_state and st.session_state['processed']:
            files = st.session_state['processed']
            
            # Check file types
            has_pdf = any(f.endswith('.pdf') for f in files)
            has_code = any(f.endswith(('.py', '.ipynb')) for f in files)
            has_data = any(f.endswith(('.csv', '.json')) for f in files)
            has_images = any(f.endswith(('.jpg', '.png', '.jpeg')) for f in files)
            
            if has_pdf:
                example_questions.extend([
                    "What are the main topics covered in the documents?",
                    "Can you summarize the key findings?",
                    "What are the important conclusions?"
                ])
            
            if has_code:
                example_questions.extend([
                    "What programming concepts are demonstrated?",
                    "Can you explain the code functionality?",
                    "What are the main functions or classes?"
                ])
            
            if has_data:
                example_questions.extend([
                    "What data patterns can you identify?",
                    "What are the key data fields or columns?",
                    "Can you summarize the data insights?"
                ])
            
            if has_images:
                example_questions.extend([
                    "What do the images show?",
                    "Can you describe the visual content?"
                ])
        
        # Fallback questions if no specific file types detected
        if not example_questions:
            example_questions = [
                "What are the main topics covered in the documents?",
                "Can you summarize the key points?", 
                "What are the important findings or conclusions?",
                "What specific information is available in the content?"
            ]
        
        for idx, question in enumerate(example_questions):
            if st.button(f"💭 {question}", key=f"chat_example_{idx}_{hash(question)}"):
                # Trigger the question as if user typed it
                st.session_state['auto_question'] = question
                st.rerun()
    
    # Handle auto-triggered questions
    if 'auto_question' in st.session_state:
        question = st.session_state.pop('auto_question')
        
        # Display user message
        display_chat_message(question, is_user=True)
        
        # Get and display bot response
        chatbot = st.session_state['chatbot']
        result = chatbot.chat(question)
        display_chat_message(result['response'], is_user=False)
        
        if result['sources']:
            display_sources(result['sources'])
        
        # Add to history
        chat_entry = {
            'user': question,
            'bot': result['response'],
            'sources': result['sources'],
            'timestamp': time.time()
        }
        st.session_state['chat_history'].append(chat_entry)
        
        st.rerun()


if __name__ == "__main__":
    chat_interface()