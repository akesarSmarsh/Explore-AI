"""BM25 search implementation for keyword-based search."""
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from rank_bm25 import BM25Okapi
import re


class BM25Search:
    """BM25 search engine for keyword-based email search."""
    
    def __init__(self, index_path: str = "./data/bm25_index.pkl"):
        """
        Initialize BM25 search.
        
        Args:
            index_path: Path to save/load the BM25 index
        """
        self.index_path = Path(index_path)
        self.bm25: Optional[BM25Okapi] = None
        self.email_ids: List[str] = []
        self.corpus: List[List[str]] = []
        
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        # Convert to lowercase and split by non-alphanumeric characters
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        
        # Filter out very short tokens
        tokens = [t for t in tokens if len(t) > 1]
        
        return tokens
    
    def build_index(self, emails: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from emails.
        
        Args:
            emails: List of email dictionaries with 'id' and 'content' keys
        """
        self.email_ids = []
        self.corpus = []
        
        for email in emails:
            email_id = email.get('id')
            content = email.get('content', '')
            
            # Combine subject and body for indexing
            subject = email.get('subject', '')
            full_text = f"{subject} {content}"
            
            tokens = self.tokenize(full_text)
            
            self.email_ids.append(email_id)
            self.corpus.append(tokens)
        
        # Build BM25 index
        self.bm25 = BM25Okapi(self.corpus)
        
        print(f"Built BM25 index with {len(self.email_ids)} emails")
    
    def search(self, query: str, n_results: int = 10) -> List[Tuple[str, float]]:
        """
        Search using BM25.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of tuples (email_id, score)
        """
        if not self.bm25 or not self.email_ids:
            return []
        
        # Tokenize query
        query_tokens = self.tokenize(query)
        
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k results
        # Create list of (email_id, score) tuples
        results = [(self.email_ids[i], scores[i]) for i in range(len(scores))]
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top n results
        return results[:n_results]
    
    def save_index(self) -> None:
        """Save BM25 index to disk."""
        if not self.bm25:
            print("No index to save")
            return
        
        # Create directory if it doesn't exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save index data
        index_data = {
            'bm25': self.bm25,
            'email_ids': self.email_ids,
            'corpus': self.corpus
        }
        
        with open(self.index_path, 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"Saved BM25 index to {self.index_path}")
    
    def load_index(self) -> bool:
        """
        Load BM25 index from disk.
        
        Returns:
            True if index was loaded successfully, False otherwise
        """
        if not self.index_path.exists():
            print(f"Index file not found at {self.index_path}")
            return False
        
        try:
            with open(self.index_path, 'rb') as f:
                index_data = pickle.load(f)
            
            self.bm25 = index_data['bm25']
            self.email_ids = index_data['email_ids']
            self.corpus = index_data['corpus']
            
            print(f"Loaded BM25 index with {len(self.email_ids)} emails from {self.index_path}")
            return True
        except Exception as e:
            print(f"Error loading BM25 index: {e}")
            return False


# Global BM25 search instance
bm25_search = BM25Search()
