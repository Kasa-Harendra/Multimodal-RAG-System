from langchain_community.document_loaders import *
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional
import time

from .embeddings import TextEmbeddings, get_image_desc, get_images_desc_batch
from .config import RAGConfig

# Preparing Documents from the input files with optimized processing
def process_input_file(input_file_name: str):
    """Process a single input file and return documents"""
    try:
        if input_file_name.endswith('.pdf'):
            return PyPDFLoader(file_path=input_file_name).load()
        elif input_file_name.endswith('.docx'):
            return Docx2txtLoader(file_path=input_file_name).load()
        elif input_file_name.endswith('.json'):
            return JSONLoader(file_path=input_file_name).load()
        elif input_file_name.endswith('.csv'):
            return CSVLoader(file_path=input_file_name).load()
        elif input_file_name.endswith('.py'):
            return PythonLoader(file_path=input_file_name).load()
        elif input_file_name.endswith('.ipynb'):
            return NotebookLoader(path=input_file_name).load()
        elif input_file_name.endswith(('.jpg', '.png', '.jpeg')):
            return get_image_desc(input_file_name)
        else:
            print(f"Unsupported file type: {input_file_name}")
            return []
    except Exception as e:
        print(f"Error processing file {input_file_name}: {e}")
        return []

def process_input_files_batch(input_file_names: List[str], max_workers: int = None) -> List:
    """Process multiple input files concurrently"""
    if not input_file_names:
        return []
    
    # Separate image files for batch processing
    image_files = [f for f in input_file_names if f.endswith(('.jpg', '.png', '.jpeg'))]
    other_files = [f for f in input_file_names if not f.endswith(('.jpg', '.png', '.jpeg'))]
    
    all_documents = []
    max_workers = max_workers or RAGConfig.DOC_PROCESSING_MAX_WORKERS or RAGConfig.get_optimal_workers("mixed")
    max_workers = min(max_workers, len(other_files)) if other_files else 4
    
    # Process images in batch (more efficient for API calls)
    if image_files:
        try:
            image_docs = get_images_desc_batch(image_files, max_workers=min(4, len(image_files)))
            all_documents.extend(image_docs)
        except Exception as e:
            print(f"Error processing image files: {e}")
    
    # Process other files concurrently
    if other_files:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(process_input_file, file_path): file_path 
                for file_path in other_files
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    documents = future.result()
                    if documents:
                        all_documents.extend(documents)
                except Exception as exc:
                    print(f'File processing failed for {file_path}: {exc}')
    
    return all_documents
    
# Obtaining splits from the documents with optimized processing
def get_splits(docs, chunk_size: int = 500, chunk_overlap: int = 100, max_workers: int = None):
    """Split documents with optional parallel processing for large document sets"""
    if not docs:
        return []
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    # For small document sets, process sequentially
    if len(docs) <= 10:
        return splitter.split_documents(documents=docs)
    
    # For large document sets, process in parallel batches
    max_workers = max_workers or min(4, len(docs) // 5)
    batch_size = max(1, len(docs) // max_workers)
    
    all_splits = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create batches of documents
        batches = [docs[i:i + batch_size] for i in range(0, len(docs), batch_size)]
        
        # Submit splitting tasks
        future_to_batch = {
            executor.submit(splitter.split_documents, batch): i 
            for i, batch in enumerate(batches)
        }
        
        # Collect results
        batch_results = [None] * len(batches)
        for future in as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                batch_results[batch_idx] = future.result()
            except Exception as exc:
                print(f'Document splitting failed for batch {batch_idx}: {exc}')
                batch_results[batch_idx] = []
        
        # Flatten results while maintaining order
        for batch_result in batch_results:
            if batch_result:
                all_splits.extend(batch_result)
    
    return all_splits

# Creating a ChromaDB to store the data for efficient retrieval with optimized embeddings
def get_db(splits, embedding_max_workers: int = None, embedding_batch_size: int = 10):
    """Create ChromaDB with optimized embedding generation"""
    if not splits:
        return None
    
    # Use optimized embedding function with concurrent processing
    embedding_fn = TextEmbeddings(
        max_workers=embedding_max_workers, 
        batch_size=embedding_batch_size
    )
    
    try:
        db = Chroma.from_documents(documents=splits, embedding=embedding_fn)
        return db
    except Exception as e:
        print(f"Error creating database: {e}")
        return None

# RAG - Documents -> Splits -> DB with optimized concurrent processing
def process_docs(session_id, uploaded_files, processed_files: list, existing_db=None, 
                max_workers: int = None, embedding_batch_size: int = None, 
                chunk_size: int = None, chunk_overlap: int = None):
    """
    Process documents with optimized concurrent processing
    
    Args:
        session_id: Session identifier
        uploaded_files: List of uploaded files
        processed_files: List of already processed file names
        existing_db: Existing database to update (optional)
        max_workers: Maximum number of worker threads (optional)
        embedding_batch_size: Batch size for embedding generation
        chunk_size: Text chunk size for splitting
        chunk_overlap: Overlap between text chunks
    """
    # Initialize configuration values with defaults
    max_workers = max_workers or RAGConfig.DOC_PROCESSING_MAX_WORKERS or RAGConfig.get_optimal_workers("mixed")
    embedding_batch_size = embedding_batch_size or RAGConfig.EMBEDDING_BATCH_SIZE
    chunk_size = chunk_size or RAGConfig.CHUNK_SIZE
    chunk_overlap = chunk_overlap or RAGConfig.CHUNK_OVERLAP
    
    if RAGConfig.ENABLE_PROGRESS_LOGGING:
        print(f"Processing {len(uploaded_files)} files with optimized concurrent processing...")
        print(f"Configuration: workers={max_workers}, batch_size={embedding_batch_size}, chunk_size={chunk_size}")
    
    start_time = time.time()
    
    all_docs = []
    new_processed = []
    temp_files = []
    
    os.makedirs('data', exist_ok=True)
    os.makedirs(f'data/{session_id}', exist_ok=True)
    
    try:
        # Save files to temp directory first
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in processed_files:
                temp_path = f"data/{session_id}/{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                temp_files.append(temp_path)
                new_processed.append(uploaded_file.name)
        
        if not temp_files:
            print("No new files to process.")
            return existing_db, processed_files
        
        print(f"Loading {len(temp_files)} files...")
        # Process files concurrently
        all_docs = process_input_files_batch(temp_files, max_workers=max_workers)
        
        if not all_docs:
            print("No documents extracted from files.")
            return existing_db, processed_files
        
        print(f"Extracted {len(all_docs)} documents. Creating text splits...")
        # Create splits with optimized processing
        splits = get_splits(all_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap, max_workers=max_workers)
        
        if not splits:
            print("No text splits created.")
            return existing_db, processed_files
        
        print(f"Created {len(splits)} text splits. Generating embeddings...")
        
        # Create or update database
        if existing_db is None:
            db = get_db(splits, embedding_max_workers=max_workers, embedding_batch_size=embedding_batch_size)
        else:
            # Use optimized embedding function for updates too
            embedding_fn = TextEmbeddings(max_workers=max_workers, batch_size=embedding_batch_size)
            try:
                existing_db.add_documents(documents=splits, embeddings=embedding_fn)
                db = existing_db
            except Exception as e:
                print(f"Error updating existing database: {e}")
                # Fallback: create new database
                db = get_db(splits, embedding_max_workers=max_workers, embedding_batch_size=embedding_batch_size)
        
        # Update processed files list
        processed_files.extend(new_processed)
        
        processing_time = time.time() - start_time
        print(f"Processing completed in {processing_time:.2f} seconds")
        print(f"Processed {len(new_processed)} files, created {len(splits)} chunks")
        
        return db, processed_files
        
    except Exception as e:
        print(f"Error during document processing: {e}")
        return existing_db, processed_files
        
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(f'data/{session_id}'):
                shutil.rmtree(f'data/{session_id}')
        except Exception as e:
            print(f"Warning: Could not clean up temporary files: {e}")