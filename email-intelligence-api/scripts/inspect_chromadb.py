"""Script to inspect ChromaDB vector store contents."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.vector_store import vector_store
from app.database import SessionLocal
from app.models import Email
import json


def inspect_chromadb():
    """Inspect ChromaDB contents and show stored emails."""
    print("=" * 80)
    print("ChromaDB Vector Store Inspector")
    print("=" * 80)
    
    # Get collection info
    collection = vector_store.collection
    count = vector_store.count()
    
    print(f"\nCollection Name: {vector_store.collection_name}")
    print(f"Total Embeddings: {count}")
    print()
    
    if count == 0:
        print("No embeddings found in the vector store.")
        return
    
    # Get all items (limited to first 100)
    limit = min(count, 100)
    print(f"Showing first {limit} items:\n")
    
    try:
        results = collection.get(
            limit=limit,
            include=["metadatas", "documents"]
        )
        
        if not results["ids"]:
            print("No items found.")
            return
        
        # Display items
        for i, item_id in enumerate(results["ids"], 1):
            metadata = results["metadatas"][i-1] if results["metadatas"] else {}
            document = results["documents"][i-1] if results["documents"] else ""
            
            print(f"{i}. UUID: {item_id}")
            print(f"   Subject: {metadata.get('subject', 'N/A')}")
            print(f"   Sender: {metadata.get('sender', 'N/A')}")
            print(f"   Date: {metadata.get('date', 'N/A')}")
            print(f"   Document Preview: {document[:100]}..." if document else "   Document: N/A")
            print()
        
        if count > limit:
            print(f"\n... and {count - limit} more items")
    
    except Exception as e:
        print(f"Error retrieving items: {e}")


def search_by_email(email_address: str):
    """Search for emails containing a specific email address."""
    print("=" * 80)
    print(f"Searching for: {email_address}")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Search in sender
        sender_emails = db.query(Email).filter(
            Email.sender.ilike(f"%{email_address}%")
        ).limit(10).all()
        
        # Search in recipients
        recipient_emails = db.query(Email).filter(
            Email.recipients.ilike(f"%{email_address}%")
        ).limit(10).all()
        
        print(f"\nFound {len(sender_emails)} emails where '{email_address}' is sender:")
        for email in sender_emails:
            print(f"  UUID: {email.id}")
            print(f"  Subject: {email.subject}")
            print(f"  Date: {email.date}")
            print()
        
        print(f"\nFound {len(recipient_emails)} emails where '{email_address}' is recipient:")
        for email in recipient_emails:
            recipients = json.loads(email.recipients) if email.recipients else []
            print(f"  UUID: {email.id}")
            print(f"  Subject: {email.subject}")
            print(f"  Sender: {email.sender}")
            print(f"  Recipients: {', '.join(recipients)}")
            print(f"  Date: {email.date}")
            print()
    
    finally:
        db.close()


def get_email_by_uuid(uuid: str):
    """Get email details by UUID."""
    print("=" * 80)
    print(f"Email Details for UUID: {uuid}")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        email = db.query(Email).filter(Email.id == uuid).first()
        
        if not email:
            print(f"\nNo email found with UUID: {uuid}")
            return
        
        recipients = json.loads(email.recipients) if email.recipients else []
        cc = json.loads(email.cc) if email.cc else []
        
        print(f"\nSubject: {email.subject}")
        print(f"Sender: {email.sender}")
        print(f"Recipients: {', '.join(recipients)}")
        print(f"CC: {', '.join(cc)}")
        print(f"Date: {email.date}")
        print(f"Message ID: {email.message_id}")
        print(f"\nBody Preview:")
        print(email.body[:500] if email.body else "N/A")
        print("\n...")
        
        # Check if in ChromaDB
        chroma_data = vector_store.get_by_id(uuid)
        if chroma_data:
            print(f"\n✓ Email exists in ChromaDB vector store")
        else:
            print(f"\n✗ Email NOT found in ChromaDB vector store")
    
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Inspect ChromaDB vector store")
    parser.add_argument("--search", "-s", help="Search for emails by email address")
    parser.add_argument("--uuid", "-u", help="Get email by UUID")
    parser.add_argument("--list", "-l", action="store_true", help="List all embeddings")
    
    args = parser.parse_args()
    
    if args.search:
        search_by_email(args.search)
    elif args.uuid:
        get_email_by_uuid(args.uuid)
    elif args.list:
        inspect_chromadb()
    else:
        # Default: show overview
        inspect_chromadb()
