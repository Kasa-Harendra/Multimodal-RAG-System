import streamlit as st
import os
import sys
import time

# Add parent directory to path for importing utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from utils.rag import process_docs
from utils.session_state import initialize_session_state
from utils.authentication import init_auth_session

# Page configuration
st.set_page_config(
    page_title="MultiModal RAG System",
    page_icon="🤖",
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
        if st.button("🔑 Go to Login", type="primary", use_container_width=True, key="app_login_btn"):
            st.switch_page("main.py")
    st.stop()

# Initialize page state - use session token as part of session ID to maintain consistency
if 'page' not in st.session_state:
    st.session_state['page'] = 'upload'

# Create consistent session ID based on user session
user_info = st.session_state.get('user_info', {})
user_id = user_info.get('user_id', 'unknown')
session_token = st.session_state.get('session_token', 'no-token')

# Use a hash of user_id and session_token for consistent session ID
import hashlib
consistent_session_id = hashlib.md5(f"{user_id}_{session_token}".encode()).hexdigest()[:12]
st.session_state['session-id'] = consistent_session_id

# Define allowed file types
ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.png', '.jpg', '.jpeg', '.csv', '.json', '.py', '.ipynb'
}

def validate_file_type(uploaded_file):
    if uploaded_file is not None:
        file_extension = uploaded_file.name.lower().split('.')[-1]
        return f'.{file_extension}' in ALLOWED_EXTENSIONS
    return False

def get_file_extension(filename):
    return f'.{filename.lower().split(".")[-1]}'

def upload_page():
    """Upload and processing page"""
    st.title("🤖 MultiModal RAG System")
    st.header("📁 Upload Your Documents")
    
    session_id = st.session_state['session-id']
    
    # Sidebar navigation
    with st.sidebar:
        
        # Logout button
        if st.button("🚪 Logout", type="secondary", use_container_width=True, key="app_upload_logout_btn"):
            # Logout user
            auth_manager = st.session_state.get('auth_manager')
            if auth_manager and 'session_token' in st.session_state:
                auth_manager.logout_user(st.session_state['session_token'])
            
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Redirect to login
            st.switch_page("main.py")
        
        # User info section
        st.header("👤 User Info")
        user_info = st.session_state.get('user_info', {})
        st.write(f"**Email:** {user_info.get('email', 'Unknown')}")
        st.write(f"**Session:** {session_id}")
        
        st.divider()
        
        st.header("🧭 Navigation")
        
        # Show current session info
        st.info(f"**Session ID:** `{session_id}`")
        
        if 'processed' in st.session_state and st.session_state['processed']:
            st.success(f"**Processed Files:** {len(st.session_state['processed'])}")
            for file in st.session_state['processed']:
                st.write(f"• {file}")
        
        st.divider()
        
        # Navigation buttons
        if st.session_state.get('db') is not None:
            if st.button("💬 Go to Chat", type="primary", use_container_width=True, key="app_sidebar_chat_btn"):
                st.session_state['page'] = 'chat'
                st.rerun()
        
        st.divider()
        
        # Performance info
        st.subheader("⚡ Performance")
        try:
            from utils.config import get_performance_info
            perf_info = get_performance_info()
            st.write(f"CPU Cores: {perf_info['system_cpu_count']}")
            st.write(f"Preset: {perf_info['recommended_preset']}")
        except ImportError:
            st.write("Performance info unavailable")

    uploaded_files = st.file_uploader(
        "Choose files",
        accept_multiple_files=True,
        help="Supported formats: PDF, DOCX, PNG, JPG, JPEG, CSV, JSON, PY, IPYNB"
    )

    if uploaded_files:
        valid_files = []
        invalid_files = []
        
        for uploaded_file in uploaded_files:
            if validate_file_type(uploaded_file):
                valid_files.append(uploaded_file)
            else:
                invalid_files.append(uploaded_file)
        
        if valid_files:
            st.success(f"✅ Successfully uploaded {len(valid_files)} valid file(s):")
            for file in valid_files:
                file_size = len(file.getvalue()) / 1024  # Size in KB
                st.write(f"📁 **{file.name}** ({file_size:.1f} KB)")
        
        # Display error for invalid files
        if invalid_files:
            st.error("❌ Invalid file type(s) detected:")
            for file in invalid_files:
                file_ext = get_file_extension(file.name)
                st.write(f"🚫 **{file.name}** - {file_ext} format is not supported")
            
            st.info("**Supported file formats:**")
            st.write("📄 Documents: PDF, DOCX")
            st.write("🖼️ Images: PNG, JPG, JPEG") 
            st.write("📊 Data: CSV, JSON")
            st.write("💻 Code: PY, IPYNB")
            st.write("\\nPlease upload files with supported formats only.")

        # Processing button
        if valid_files and st.button('🚀 Start Processing', type="primary", key="app_start_processing_btn"):
            processed_files = st.session_state['processed']
            existing_db = st.session_state['db']
            
            # # Show performance settings in an expander
            # with st.expander("⚙️ Performance Settings", expanded=False):
            #     col1, col2 = st.columns(2)
            #     with col1:
            #         st.write("**Current Configuration:**")
            #         # Import config here to avoid import issues
            #         try:
            #             from utils.config import RAGConfig, get_performance_info
            #             perf_info = get_performance_info()
            #             st.write(f"CPU Cores: {perf_info['system_cpu_count']}")
            #             st.write(f"Recommended Preset: {perf_info['recommended_preset']}")
            #         except ImportError:
            #             st.write("Performance info unavailable")
                
            #     with col2:
            #         st.write("**Optimizations Enabled:**")
            #         st.write("✅ Concurrent file processing")
            #         st.write("✅ Batch embedding generation")
            #         st.write("✅ Parallel image processing")
            #         st.write("✅ Connection pooling")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            start_time = time.time()
            
            with st.spinner("🚀 Processing files with optimized multithreading..."):
                status_text.text("Initializing processing...")
                progress_bar.progress(10)
                
                try:
                    status_text.text("Loading and processing files...")
                    progress_bar.progress(30)
                    
                    # Use optimized processing
                    st.session_state['db'], st.session_state['processed'] = process_docs(
                        session_id, valid_files, processed_files, existing_db=existing_db
                    )
                    progress_bar.progress(90)
                    
                    status_text.text("Finalizing database...")
                    progress_bar.progress(100)
                    
                    processing_time = time.time() - start_time
                    
                    if existing_db is None:
                        st.success(f"✅ Database created successfully in {processing_time:.2f} seconds!")
                    else: 
                        st.success(f"✅ Database updated successfully in {processing_time:.2f} seconds!")
                    
                    # Show processing statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Files Processed", len(valid_files))
                    with col2:
                        st.metric("Processing Time", f"{processing_time:.1f}s")
                    with col3:
                        if processing_time > 0:
                            st.metric("Files/Second", f"{len(valid_files)/processing_time:.1f}")
                    
                    # Show chat button prominently
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button('💬 Start Chatting Now!', type="primary", use_container_width=True, key="app_start_chatting_btn"):
                            st.session_state['page'] = 'chat'
                            st.rerun()
                            
                except Exception as e:
                    st.error(f"❌ Processing failed: {str(e)}")
                    st.write("Try using the performance optimizer script to adjust settings.")
                finally:
                    progress_bar.empty()
                    status_text.empty()

    # Display upload instructions when no files are uploaded
    else:
        st.info("👆 Please select one or more files to upload")
        
        with st.expander("📋 Supported File Types"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📄 Documents:**")
                st.write("• PDF files (.pdf)")
                st.write("• Word documents (.docx)")
                st.write("")
                st.write("**🖼️ Images:**")
                st.write("• PNG images (.png)")
                st.write("• JPEG images (.jpg, .jpeg)")
            
            with col2:
                st.write("**📊 Data Files:**")
                st.write("• CSV files (.csv)")
                st.write("• JSON files (.json)")
                st.write("")
                st.write("**💻 Code Files:**")
                st.write("• Python scripts (.py)")
                st.write("• Jupyter notebooks (.ipynb)")


def chat_page():
    """Chat interface page"""
    # Import and show the chat interface directly
    # The chat interface handles its own sidebar content
    from pages.chat import chat_interface
    chat_interface()


# Main app logic
def main():
    """Main application logic with page routing"""
    
    # Check current page and display appropriate interface
    if st.session_state['page'] == 'upload':
        upload_page()
    elif st.session_state['page'] == 'chat':
        chat_page()
    else:
        # Default to upload page
        st.session_state['page'] = 'upload'
        upload_page()


if __name__ == "__main__":
    main()