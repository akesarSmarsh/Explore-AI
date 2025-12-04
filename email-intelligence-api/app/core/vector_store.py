"""ChromaDB vector store for semantic search."""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.api.models.Collection import Collection

from app.database import get_chroma_collection


class VectorStore:
    """Vector store for email embeddings using ChromaDB."""
    
    def __init__(self, collection_name: str = "email_embeddings"):
        """Initialize the vector store."""
        self.collection_name = collection_name
        self._collection: Optional[Collection] = None
    
    @property
    def collection(self) -> Collection:
        """Get or create the ChromaDB collection."""
        if self._collection is None:
            self._collection = get_chroma_collection(self.collection_name)
        return self._collection
    
    def add_embedding(
        self,
        id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[str] = None
    ):
        """
        Add a single embedding to the store.
        
        Args:
            id: Unique identifier (email_id)
            embedding: The embedding vector
            metadata: Optional metadata dict
            document: Optional document text
        """
        self.collection.add(
            ids=[id],
            embeddings=[embedding],
            metadatas=[metadata] if metadata else None,
            documents=[document] if document else None
        )
    
    def add_embeddings_batch(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None
    ):
        """
        Add multiple embeddings to the store.
        
        Args:
            ids: List of unique identifiers
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dicts
            documents: Optional list of document texts
        """
        if not ids:
            return
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: The query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter
            where_document: Optional document content filter
            
        Returns:
            Dict with ids, distances, metadatas, and documents
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["metadatas", "documents", "distances"]
        )
        
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "documents": results["documents"][0] if results["documents"] else []
        }
    
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific embedding by ID.
        
        Args:
            id: The embedding ID
            
        Returns:
            Dict with embedding data or None
        """
        results = self.collection.get(
            ids=[id],
            include=["embeddings", "metadatas", "documents"]
        )
        
        if not results["ids"]:
            return None
        
        return {
            "id": results["ids"][0],
            "embedding": results["embeddings"][0] if results["embeddings"] else None,
            "metadata": results["metadatas"][0] if results["metadatas"] else None,
            "document": results["documents"][0] if results["documents"] else None
        }
    
    def find_similar(
        self,
        id: str,
        n_results: int = 10,
        exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find similar items to a given ID.
        
        Args:
            id: The source embedding ID
            n_results: Number of results
            exclude_self: Whether to exclude the source item
            
        Returns:
            List of similar items with scores
        """
        # Get the source embedding
        source = self.get_by_id(id)
        if not source or not source["embedding"]:
            return []
        
        # Search for similar
        results = self.search(
            query_embedding=source["embedding"],
            n_results=n_results + (1 if exclude_self else 0)
        )
        
        similar = []
        for i, result_id in enumerate(results["ids"]):
            if exclude_self and result_id == id:
                continue
            
            similar.append({
                "id": result_id,
                "distance": results["distances"][i] if results["distances"] else None,
                "score": 1 - results["distances"][i] if results["distances"] else None,
                "metadata": results["metadatas"][i] if results["metadatas"] else None
            })
        
        return similar[:n_results]
    
    def delete(self, ids: List[str]):
        """Delete embeddings by ID."""
        if ids:
            self.collection.delete(ids=ids)
    
    def count(self) -> int:
        """Get total count of embeddings."""
        return self.collection.count()
    
    def reset(self):
        """Reset the collection (delete all data)."""
        self._collection = None
        from app.database import chroma_client
        try:
            chroma_client.delete_collection(self.collection_name)
        except ValueError:
            pass  # Collection doesn't exist


# Global instance
vector_store = VectorStore()

