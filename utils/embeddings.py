from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain_community.docstore.document import Document
import requests
import base64
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import List
import os
import time
from .config import RAGConfig
import streamlit as st

# Embeddings Function for Text with Multithreading Support
class TextEmbeddings(EmbeddingFunction):
    def __init__(self, max_workers: int = None, batch_size: int = None):
        super().__init__()
        self.max_workers = max_workers or RAGConfig.EMBEDDING_MAX_WORKERS or RAGConfig.get_optimal_workers("io")
        self.batch_size = batch_size or RAGConfig.EMBEDDING_BATCH_SIZE
        self._session = requests.Session() if RAGConfig.USE_SESSION_POOLING else None
    
    def embed(self, string: str):
        """Single embedding generation"""
        session = self._session or requests
        
        for attempt in range(RAGConfig.MAX_RETRIES):
            try:
                api_key =  str(st.secrets.get('OLLAMA-API-KEY'))
                
                response = session.post(
                    url="https://aihub-vvitu.social/api/ollama-api/embed/",
                    headers={'API-KEY': api_key},
                    json={
                        'model': 'qwen3-embedding:8b',
                        'input': string
                    },
                    timeout=RAGConfig.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response.json()['embeddings'][0]
            except Exception as e:
                if attempt == RAGConfig.MAX_RETRIES - 1:
                    raise e
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts concurrently"""
        embeddings = [None] * len(texts)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all embedding tasks
            future_to_index = {
                executor.submit(self.embed, text): i 
                for i, text in enumerate(texts)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    embeddings[index] = future.result()
                except Exception as exc:
                    print(f'Embedding generation failed for text {index}: {exc}')
                    # Return a zero vector as fallback
                    embeddings[index] = [0.0] * 1024  # Adjust dimension as needed
        
        return embeddings
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents with batch processing and concurrency"""
        if not texts:
            return []
        
        all_embeddings = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        return self.embed(text)
    
# Describing the Image with optimized processing
def encode_image_to_base64(image_path):
    """Helper function to encode image to base64"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def get_image_desc(img):
    """Get description for a single image"""
    img_64 = encode_image_to_base64(img)    
    
    api_key =  str(st.secrets.get('OLLAMA-API-KEY'))
    
    response = requests.post(
        url="https://aihub-vvitu.social/api/ollama-api/generate/",
        headers={
            'API-KEY': api_key
        },
        json={
            "model": "moondream:latest",
            "prompt": "Describe the image in detail",
            "images": [img_64],
            "stream":False
        }
    )
    response.raise_for_status()
    return [Document(metadata={'file_name': img}, page_content=response.json()['response'])]

def get_images_desc_batch(image_paths: List[str], max_workers: int = None) -> List[Document]:
    """Process multiple images concurrently"""
    if not image_paths:
        return []
    
    max_workers = max_workers or RAGConfig.IMAGE_MAX_WORKERS or min(8, len(image_paths))
    all_documents = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all image processing tasks
        future_to_path = {
            executor.submit(get_image_desc, img_path): img_path 
            for img_path in image_paths
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_path):
            img_path = future_to_path[future]
            try:
                documents = future.result()
                all_documents.extend(documents)
            except Exception as exc:
                print(f'Image processing failed for {img_path}: {exc}')
                # Create a fallback document
                all_documents.append(
                    Document(
                        metadata={'file_name': img_path}, 
                        page_content=f"Failed to process image: {img_path}"
                    )
                )
    
    return all_documents