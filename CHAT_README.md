# 🤖 MultiModal RAG Chat System

A sophisticated chat interface that allows you to interact with your uploaded documents using Retrieval-Augmented Generation (RAG) technology.

## ✨ Features

### 🧠 **Intelligent Document Understanding**
- **Context-Aware Responses**: The chatbot understands your documents and provides answers based on their content
- **Multi-Document Support**: Queries across all your uploaded files simultaneously
- **Smart Retrieval**: Uses advanced similarity search to find the most relevant information

### 💬 **Advanced Chat Capabilities**
- **Conversation Memory**: Maintains context across multiple exchanges
- **Query Enhancement**: Automatically improves your questions for better results
- **Source Citations**: Shows which documents were used to generate each response
- **Dynamic Examples**: Suggests relevant questions based on your uploaded content

### 📊 **Real-Time Analytics**
- **Relevance Scoring**: Shows how relevant retrieved documents are to your query
- **Source Tracking**: Displays metadata and context for each retrieved document
- **Performance Metrics**: Shows processing time and number of sources used

## 🚀 How to Use

### 1. **Upload Documents**
Navigate to the upload page and add your files:
- 📄 **Documents**: PDF, DOCX files
- 🖼️ **Images**: PNG, JPG, JPEG (with AI description)
- 📊 **Data**: CSV, JSON files
- 💻 **Code**: Python files, Jupyter notebooks

### 2. **Process Documents**
Click "Start Processing" to:
- Extract text content from all files
- Generate embeddings using advanced AI models
- Create a searchable vector database
- Enable optimized retrieval

### 3. **Start Chatting**
Click "Chat Now" or navigate to the chat interface to:
- Ask questions about your documents
- Get contextual responses based on the content
- View source citations and relevance scores
- Continue conversations with memory

## 💡 Example Queries

### 📚 **General Questions**
```
- "What are the main topics covered in the documents?"
- "Can you summarize the key findings?"
- "What are the most important conclusions?"
```

### 🔍 **Specific Searches**
```
- "What does the document say about [specific topic]?"
- "Find information related to [keyword]"
- "What data is available about [subject]?"
```

### 📊 **Analysis Questions**
```
- "Compare the different approaches mentioned"
- "What are the advantages and disadvantages discussed?"
- "What trends or patterns can you identify?"
```

### 💻 **Code-Specific Questions**
```
- "What programming concepts are demonstrated?"
- "Explain how this function works"
- "What are the main classes and their purposes?"
```

## 🔧 Technical Architecture

### **RAG Pipeline**
```
User Query → Query Enhancement → Vector Search → Context Retrieval → LLM Generation → Response + Sources
```

### **Key Components**

1. **Query Enhancement**
   - Generates alternative phrasings of your question
   - Improves retrieval accuracy
   - Handles different question types intelligently

2. **Vector Search**
   - Uses ChromaDB for fast similarity search
   - Configurable relevance thresholds
   - Multi-query fusion for better results

3. **Context Assembly**
   - Combines relevant document chunks
   - Removes duplicates while preserving order
   - Limits context size for optimal processing

4. **Response Generation**
   - Uses advanced language models (Qwen2.5:7b)
   - Maintains conversation history
   - Provides structured, informative responses

## ⚙️ Configuration Options

### **Search Settings**
- **Context Chunks**: Number of document segments to retrieve (default: 7)
- **Relevance Threshold**: Minimum similarity score for inclusion
- **Source Limit**: Maximum number of sources to display (default: 3)

### **Response Settings**
- **Temperature**: Controls creativity vs. factuality (default: 0.7)
- **Max Tokens**: Maximum response length (default: 1000)
- **Context Window**: Amount of conversation history to maintain

## 🎯 Best Practices

### **For Better Results**
1. **Be Specific**: Ask focused questions rather than very broad ones
2. **Use Keywords**: Include important terms from your documents
3. **Follow Up**: Build on previous responses for deeper insights
4. **Check Sources**: Review cited documents to verify information

### **Question Types That Work Well**
- ✅ **Factual queries**: "What is X?", "When did Y happen?"
- ✅ **Summary requests**: "Summarize the main points about Z"
- ✅ **Comparison questions**: "How does A differ from B?"
- ✅ **Explanatory questions**: "How does X work?", "Why does Y occur?"

### **Optimization Tips**
- 📁 **Organize files**: Group related documents for better context
- 🏷️ **Use descriptive names**: Help the system understand file content
- 📝 **Clear questions**: Well-formed questions get better answers
- 🔄 **Iterate**: Refine questions based on initial responses

## 🛠️ Troubleshooting

### **Common Issues**

**"No relevant context found"**
- Try rephrasing your question with different keywords
- Check if your documents actually contain the requested information
- Use broader terms initially, then narrow down

**"Response seems inaccurate"**
- Check the source citations to verify information
- The AI might be making connections between separate pieces of information
- Try asking for specific quotes or references

**"Slow response time"**
- Large documents take more time to process
- Complex questions require more computation
- Check your internet connection for API calls

**"Chat history not maintained"**
- Ensure you're staying in the same session
- Browser refresh clears conversation memory
- Use the "Clear Chat History" button to reset if needed

## 🔐 Privacy & Security

- **Local Processing**: Documents are processed locally when possible
- **Session Isolation**: Each session maintains separate data
- **Temporary Storage**: Uploaded files are deleted after processing
- **No Persistence**: Chat history is not saved permanently

## 🚀 Advanced Features

### **Multi-File Analysis**
The system can correlate information across multiple documents:
```
"Compare the findings in document A with the conclusions in document B"
```

### **Image Understanding**
When images are uploaded, the system:
- Generates detailed descriptions using AI vision models
- Includes visual content in searchable text
- Allows questions about visual elements

### **Code Analysis**
For programming files, the system can:
- Explain code functionality
- Identify patterns and best practices
- Suggest improvements or alternatives

## 📈 Performance Metrics

The chat interface displays real-time metrics:
- **Processing Time**: How long it took to generate the response
- **Sources Used**: Number of document chunks referenced
- **Relevance Score**: Quality of document matching
- **Context Quality**: Amount of relevant information found

---

*Built with advanced RAG technology, featuring optimized vector search, intelligent query processing, and state-of-the-art language models for accurate, context-aware responses.*