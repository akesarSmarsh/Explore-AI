"""Text embedding processor using sentence-transformers."""
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingProcessor:
    """Generate text embeddings for semantic search."""
    
    _instance: Optional["EmbeddingProcessor"] = None
    _model: Optional[SentenceTransformer] = None
    
    def __new__(cls):
        """Singleton pattern for embedding processor."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the embedding processor."""
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model."""
        print(f"Loading embedding model: {settings.embedding_model}")
        self._model = SentenceTransformer(settings.embedding_model)
        print("Embedding model loaded successfully")
    
    def encode(self, text: str) -> List[float]:
        """
        Encode a single text into an embedding vector.
        
        Args:
            text: Text to encode
            
        Returns:
            List of floats representing the embedding
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self._model.get_sentence_embedding_dimension()
        
        # Truncate long texts (model has max sequence length)
        max_length = 512  # tokens
        if len(text) > max_length * 4:  # rough char estimate
            text = text[:max_length * 4]
        
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encode multiple texts into embedding vectors.
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Clean and truncate texts
        processed_texts = []
        for text in texts:
            if not text or not text.strip():
                processed_texts.append("")
            elif len(text) > 2048:
                processed_texts.append(text[:2048])
            else:
                processed_texts.append(text)
        
        embeddings = self._model.encode(
            processed_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True
        )
        
        return embeddings.tolist()
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embedding vectors."""
        return self._model.get_sentence_embedding_dimension()
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# Global instance
embedding_processor = EmbeddingProcessor()

