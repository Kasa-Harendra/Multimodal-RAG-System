# 🤖 MultiModal RAG Chat System

A sophisticated chat interface that lets you interact with your uploaded documents using Retrieval‑Augmented Generation (RAG) technology.

## ✨ Features

### 🧠 Intelligent Document Understanding
- **Context‑Aware Responses**: The chatbot understands the content of your uploaded files and answers questions based on that content.
- **Multi‑Document Support**: Queries span all uploaded files at once.
- **Smart Retrieval**: Advanced similarity search (vector search) fetches the most relevant information.

### 📊 Session & Conversation Management
- **Conversation Memory**: Maintains context across multiple exchanges.
- **Source Citations**: Displays which documents were used for each answer.
- **Dynamic Examples**: Suggests questions tailored to the types of files you have uploaded.
- **Query Enhancement**: Automatically generates variations of your question to improve retrieval.

### 🧬 Multi‑Modal Support
- Handles PDFs, images, spreadsheets, JSON, CSV, Python scripts, and Jupyter notebooks.

### ⚙️ Architecture
```User Query → Query Enhancement → Vector Search → Context Retrieval → LLM Generation → Response + Sources```

## 🚀 Getting Started

1. **Upload documents**:  
   Use the *Upload* page to add PDFs, images, code files, or spreadsheets.
2. **Process**:  
   The system will parse the files, split them into chunks, embed them into a vector store (ChromaDB), and prepare metadata.
3. **Chat**:  
   Switch to the *Chat* page to ask questions about your documents. The chatbot will retrieve relevant snippets, pass them to an LLM (via the OLLAMA API), and return an answer along with source citations.

## 🔧 Technical Architecture

- **RAG Pipeline**
  ```User Query → Query Enhancement → Vector Search → Context Retrieval → LLM Generation → Response + Sources```

- **Key Modules**
 -  `app/pages/app.py` – Handles file upload, preprocessing, and session management.
 - `app/pages/chat.py` – Implements the chat UI, conversation memory, and dynamic question suggestions.
 - `embeddings.py` – Provides the embedding logic for vector search.
 - `utils/file.py` – Utilities for file parsing (PDF, images, CSV, JSON, code).
 - `CHAT_README.md` – Contains feature highlights and example prompts.

## 📜 Example Questions

Based on the file types you upload, the system suggests relevant questions, e.g.:

- For PDFs: *“What are the main topics covered?”*
- For code: *“What programming concepts are demonstrated?”*
- For data files: *“What data patterns can you identify?”*
