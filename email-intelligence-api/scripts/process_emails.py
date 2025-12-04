"""Process Enron emails: parse, extract entities, generate embeddings."""
import os
import sys
import csv
import json
import email
from email import policy
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import re

# Increase CSV field size limit to handle large email bodies
csv.field_size_limit(10 * 1024 * 1024)  # 10 MB limit

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import init_db, SessionLocal
from app.models import Email, Entity
from app.core.ner_processor import NERProcessor
from app.core.embeddings import EmbeddingProcessor
from app.core.vector_store import VectorStore
from app.services.alert_service import AlertService


def parse_email_message(raw_message: str) -> Dict[str, Any]:
    """Parse raw email message into structured data."""
    try:
        msg = email.message_from_string(raw_message, policy=policy.default)
    
        message_id = msg.get("Message-ID", "")
        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        
        to_field = msg.get("To", "")
        recipients = [r.strip() for r in to_field.split(",") if r.strip()]
        
        cc_field = msg.get("Cc", "")
        cc = [c.strip() for c in cc_field.split(",") if c.strip()]

        date_str = msg.get("Date", "")
        date = None
        if date_str:
            try:
                date_str = re.sub(r'\s+\([A-Z]+\)$', '', date_str)  # Remove timezone abbrev
                for fmt in [
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%a, %d %b %Y %H:%M:%S",
                    "%d %b %Y %H:%M:%S %z",
                    "%d %b %Y %H:%M:%S",
                ]:
                    try:
                        date = datetime.strptime(date_str.strip(), fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_content()
                        break
                    except Exception:
                        body = str(part.get_payload(decode=True), errors='ignore')
        else:
            try:
                body = msg.get_content()
            except Exception:
                body = str(msg.get_payload(decode=True), errors='ignore')
        
        return {
            "message_id": message_id,
            "subject": subject,
            "sender": sender,
            "recipients": recipients,
            "cc": cc,
            "date": date,
            "body": body
        }
    
    except Exception as e:
        print(f"Error parsing email: {e}")
        return None


def process_csv_file(
    csv_path: str,
    limit: Optional[int] = None,
    batch_size: int = 100
) -> int:
    """
    Process emails from CSV file.
    
    Args:
        csv_path: Path to the CSV file
        limit: Maximum number of emails to process
        batch_size: Batch size for database commits
        
    Returns:
        Number of emails processed
    """
    print(f"Processing: {csv_path}")
    
    # Initialize components
    init_db()
    db = SessionLocal()
    ner_processor = NERProcessor()
    embedding_processor = EmbeddingProcessor()
    vector_store = VectorStore()
    alert_service = AlertService(db)
    
    # Seed default alert rules
    alert_service.seed_default_rules()
    
    processed = 0
    errors = 0
    batch_emails = []
    batch_embeddings = []
    batch_ids = []
    batch_metadatas = []
    batch_documents = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                if limit and processed >= limit:
                    break
                
                try:
                    # Get raw message
                    raw_message = row.get('message', '')
                    if not raw_message:
                        continue
                    
                    # Parse email
                    parsed = parse_email_message(raw_message)
                    if not parsed or not parsed.get('body'):
                        continue
                    
                    # Create email record
                    email_obj = Email(
                        message_id=parsed['message_id'],
                        subject=parsed['subject'],
                        sender=parsed['sender'],
                        recipients=json.dumps(parsed['recipients']),
                        cc=json.dumps(parsed['cc']),
                        date=parsed['date'],
                        body=parsed['body'],
                        raw_file_path=row.get('file', '')
                    )
                    db.add(email_obj)
                    db.flush()  # Get ID
                    
                    # Extract entities
                    entities = ner_processor.extract_entities(parsed['body'])
                    for ent_data in entities:
                        entity = Entity(
                            email_id=email_obj.id,
                            text=ent_data['text'],
                            type=ent_data['type'],
                            start_pos=ent_data['start_pos'],
                            end_pos=ent_data['end_pos'],
                            sentence=ent_data.get('sentence')
                        )
                        db.add(entity)
                    
                    # Prepare for batch embedding
                    batch_emails.append(email_obj)
                    batch_ids.append(email_obj.id)
                    batch_documents.append(parsed['body'][:1000])
                    batch_metadatas.append({
                        "subject": parsed['subject'] or "",
                        "sender": parsed['sender'] or "",
                        "date": parsed['date'].isoformat() if parsed['date'] else ""
                    })
                    
                    processed += 1
                    
                    # Process batch
                    if len(batch_emails) >= batch_size:
                        # Generate embeddings
                        texts = [e.body for e in batch_emails]
                        embeddings = embedding_processor.encode_batch(texts)
                        
                        # Add to vector store
                        vector_store.add_embeddings_batch(
                            ids=batch_ids,
                            embeddings=embeddings,
                            metadatas=batch_metadatas,
                            documents=batch_documents
                        )
                        
                        # Evaluate alerts
                        for email_obj in batch_emails:
                            alert_service.evaluate_email(email_obj)
                        
                        # Commit batch
                        db.commit()
                        
                        print(f"Processed {processed} emails...")
                        
                        # Clear batch
                        batch_emails = []
                        batch_ids = []
                        batch_embeddings = []
                        batch_metadatas = []
                        batch_documents = []
                
                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        print(f"Error processing row {i}: {e}")
                    db.rollback()
        
        # Process remaining batch
        if batch_emails:
            texts = [e.body for e in batch_emails]
            embeddings = embedding_processor.encode_batch(texts)
            
            vector_store.add_embeddings_batch(
                ids=batch_ids,
                embeddings=embeddings,
                metadatas=batch_metadatas,
                documents=batch_documents
            )
            
            for email_obj in batch_emails:
                alert_service.evaluate_email(email_obj)
            
            db.commit()
    
    finally:
        db.close()
    
    print(f"\n{'=' * 60}")
    print(f"Processing complete!")
    print(f"Emails processed: {processed}")
    print(f"Errors: {errors}")
    print(f"{'=' * 60}")
    
    return processed


def find_emails_csv():
    """Find the emails.csv file in common locations."""
    possible_paths = [
        Path("data/raw/emails.csv"),
        Path("../emails.csv"),  # Parent directory (workspace root)
        Path("emails.csv"),
        Path("../data/raw/emails.csv"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path.resolve())
    
    return None


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process Enron emails")
    parser.add_argument(
        "--input",
        default=None,
        help="Input CSV file path (auto-detected if not provided)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum emails to process"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for processing"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Process sample data instead"
    )
    
    args = parser.parse_args()
    
    if args.sample:
        csv_path = "data/raw/sample_emails.csv"
        if not Path(csv_path).exists():
            from scripts.download_data import create_sample_data
            create_sample_data()
    elif args.input:
        csv_path = args.input
    else:
        # Auto-detect emails.csv location
        csv_path = find_emails_csv()
        if csv_path:
            print(f"Found emails.csv at: {csv_path}")
        else:
            print("Error: Could not find emails.csv")
            print("Please specify the path with --input or place emails.csv in:")
            print("  - data/raw/emails.csv")
            print("  - ../emails.csv (workspace root)")
            sys.exit(1)
    
    if not Path(csv_path).exists():
        print(f"Error: File not found: {csv_path}")
        print("Run 'python scripts/download_data.py' first to download the dataset.")
        sys.exit(1)
    
    # Use limit from args or default sample size
    limit = args.limit if args.limit is not None else settings.sample_size
    print(f"Processing up to {limit} emails...")
    
    process_csv_file(
        csv_path=csv_path,
        limit=limit,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()

