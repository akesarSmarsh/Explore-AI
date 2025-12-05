"""Build BM25 index from existing emails."""
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Email
from app.core.bm25_search import bm25_search


def build_bm25_index():
    """Build BM25 index from all emails in the database."""
    print("Building BM25 index from emails...")
    
    db = SessionLocal()
    try:
        # Fetch all emails
        emails = db.query(Email).all()
        
        if not emails:
            print("No emails found in database. Please process emails first.")
            return
        
        print(f"Found {len(emails)} emails")
        
        # Prepare email data for indexing
        email_data = []
        for email in emails:
            email_data.append({
                'id': email.id,
                'subject': email.subject or '',
                'content': email.body or ''
            })
        
        # Build index
        bm25_search.build_index(email_data)
        
        # Save index to disk
        bm25_search.save_index()
        
        print("BM25 index built successfully!")
        
    finally:
        db.close()


if __name__ == "__main__":
    build_bm25_index()
