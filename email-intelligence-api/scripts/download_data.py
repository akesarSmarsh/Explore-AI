"""Download and extract Enron email sample dataset."""
import os
import sys
import zipfile
import tarfile
import shutil
from pathlib import Path
import urllib.request

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_enron_sample(output_dir: str = "data/raw", sample_size: int = 10000):
    """
    Download Enron email dataset sample.
    
    Note: The full dataset is ~1.5GB. This script provides instructions
    for downloading from Kaggle or uses a smaller sample.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Enron Email Dataset Download")
    print("=" * 60)
    print()
    print("The Enron dataset must be downloaded from Kaggle:")
    print("https://www.kaggle.com/datasets/wcukierski/enron-email-dataset")
    print()
    print("Steps:")
    print("1. Go to the Kaggle link above")
    print("2. Click 'Download' (requires Kaggle account)")
    print("3. Extract the downloaded file")
    print("4. Place the 'emails.csv' file in: data/raw/")
    print()
    print("Alternative - Using Kaggle CLI:")
    print("  pip install kaggle")
    print("  kaggle datasets download -d wcukierski/enron-email-dataset")
    print("  unzip enron-email-dataset.zip -d data/raw/")
    print()
    
    # Check if data already exists
    csv_path = output_path / "emails.csv"
    if csv_path.exists():
        print(f"✓ Found existing data: {csv_path}")
        return str(csv_path)
    
    print("After downloading, run: python scripts/process_emails.py")
    print("=" * 60)
    
    return None


def create_sample_data(output_dir: str = "data/raw"):
    """Create sample email data for testing."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    sample_csv = output_path / "sample_emails.csv"
    
    # Sample emails for testing
    sample_emails = '''file,message
"sample/1.txt","Message-ID: <test1@enron.com>
Date: Mon, 14 May 2001 16:39:00 -0700 (PDT)
From: john.smith@enron.com
To: jane.doe@enron.com
Subject: Q2 Financial Review Meeting

Hi Jane,

I wanted to follow up on our discussion about the Q2 financial review. 
Ken Lay will be joining us on Tuesday at 2 PM in the Houston office.

The quarterly revenue is approximately $50 million, which exceeds our projections.
Please prepare the SEC filing documents before the meeting.

Best regards,
John Smith
VP of Finance
Enron Corporation"
"sample/2.txt","Message-ID: <test2@enron.com>
Date: Tue, 15 May 2001 09:15:00 -0700 (PDT)
From: jane.doe@enron.com
To: john.smith@enron.com, jeff.skilling@enron.com
Subject: Re: Q2 Financial Review Meeting

John,

Thanks for the update. I've prepared the documents for the SEC.
Andrew Fastow mentioned some concerns about the LJM partnership structure.

The total assets are valued at $65 billion according to Arthur Andersen's audit.

I'll see you Tuesday at the meeting in Houston.

Jane Doe
Senior Analyst"
"sample/3.txt","Message-ID: <test3@enron.com>
Date: Wed, 16 May 2001 11:30:00 -0700 (PDT)
From: sherron.watkins@enron.com
To: ken.lay@enron.com
Subject: Accounting Concerns

Dear Mr. Lay,

I am incredibly nervous that we will implode in a wave of accounting scandals.
The Raptor and Condor transactions seem problematic.

I have discussed my concerns with the legal department in New York.
We need to review these $1.2 billion positions immediately.

Please contact me at (713) 555-0123 to discuss.

Sherron Watkins
VP of Corporate Development"
"sample/4.txt","Message-ID: <test4@enron.com>
Date: Thu, 17 May 2001 14:00:00 -0700 (PDT)
From: jeff.skilling@enron.com
To: all-employees@enron.com
Subject: Company Performance Update

Team,

I'm pleased to report that Enron's stock price reached $90 per share today.
Our California operations generated $200 million in trading revenue.

The board meeting in Chicago next Monday will discuss the expansion plans.
We expect to add 1,000 new employees by end of year.

Jeff Skilling
CEO, Enron Corporation"
"sample/5.txt","Message-ID: <test5@enron.com>
Date: Fri, 18 May 2001 10:45:00 -0700 (PDT)
From: andrew.fastow@enron.com  
To: michael.kopper@enron.com
Subject: LJM Investment Structure

Michael,

Please ensure all documents related to the LJM2 partnership are properly filed.
The FBI has been asking questions about off-balance-sheet entities.

Transfer the $30 million to the Cayman Islands account before month end.
Delete any sensitive communications regarding the SPE transactions.

Andrew Fastow
CFO"
'''
    
    with open(sample_csv, 'w', encoding='utf-8') as f:
        f.write(sample_emails)
    
    print(f"✓ Created sample data: {sample_csv}")
    return str(sample_csv)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Enron email dataset")
    parser.add_argument("--sample", action="store_true", help="Create sample data for testing")
    parser.add_argument("--output", default="data/raw", help="Output directory")
    
    args = parser.parse_args()
    
    if args.sample:
        create_sample_data(args.output)
    else:
        download_enron_sample(args.output)

