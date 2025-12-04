"""Simple web-based ChromaDB viewer using Flask."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template_string, jsonify, request
from app.core.vector_store import vector_store
from app.database import SessionLocal
from app.models import Email
import json

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ChromaDB Viewer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .stats {
            background: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .search-box {
            margin: 20px 0;
        }
        input[type="text"] {
            width: 70%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            padding: 10px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #45a049;
        }
        .email-card {
            border: 1px solid #ddd;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            background: #fafafa;
        }
        .email-card:hover {
            background: #f0f0f0;
        }
        .uuid {
            font-family: monospace;
            color: #666;
            font-size: 12px;
        }
        .subject {
            font-weight: bold;
            color: #333;
            margin: 5px 0;
        }
        .meta {
            color: #666;
            font-size: 14px;
        }
        .preview {
            color: #888;
            font-size: 13px;
            margin-top: 10px;
            font-style: italic;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 ChromaDB Vector Store Viewer</h1>
        
        <div class="stats">
            <strong>Collection:</strong> <span id="collection-name">Loading...</span><br>
            <strong>Total Embeddings:</strong> <span id="total-count">Loading...</span>
        </div>
        
        <div class="search-box">
            <input type="text" id="search-input" placeholder="Search by email address (sender or recipient)...">
            <button onclick="searchEmails()">Search</button>
            <button onclick="loadAll()">Show All</button>
        </div>
        
        <div id="results">
            <div class="loading">Loading...</div>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('collection-name').textContent = data.collection_name;
                document.getElementById('total-count').textContent = data.count;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        async function loadAll() {
            document.getElementById('results').innerHTML = '<div class="loading">Loading...</div>';
            try {
                const response = await fetch('/api/list?limit=50');
                const data = await response.json();
                displayResults(data.items);
            } catch (error) {
                document.getElementById('results').innerHTML = 
                    '<div class="error">Error loading data: ' + error.message + '</div>';
            }
        }
        
        async function searchEmails() {
            const query = document.getElementById('search-input').value.trim();
            if (!query) {
                alert('Please enter a search term');
                return;
            }
            
            document.getElementById('results').innerHTML = '<div class="loading">Searching...</div>';
            try {
                const response = await fetch('/api/search?q=' + encodeURIComponent(query));
                const data = await response.json();
                displayResults(data.items);
            } catch (error) {
                document.getElementById('results').innerHTML = 
                    '<div class="error">Error searching: ' + error.message + '</div>';
            }
        }
        
        function displayResults(items) {
            if (!items || items.length === 0) {
                document.getElementById('results').innerHTML = 
                    '<div class="loading">No results found</div>';
                return;
            }
            
            let html = '<h2>Results (' + items.length + ')</h2>';
            items.forEach(item => {
                html += `
                    <div class="email-card">
                        <div class="uuid">UUID: ${item.uuid}</div>
                        <div class="subject">${item.subject || 'No Subject'}</div>
                        <div class="meta">
                            <strong>From:</strong> ${item.sender || 'N/A'}<br>
                            <strong>To:</strong> ${item.recipients || 'N/A'}<br>
                            <strong>Date:</strong> ${item.date || 'N/A'}
                        </div>
                        ${item.preview ? '<div class="preview">' + item.preview + '</div>' : ''}
                    </div>
                `;
            });
            document.getElementById('results').innerHTML = html;
        }
        
        // Load stats on page load
        loadStats();
        loadAll();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def get_stats():
    """Get collection statistics."""
    count = vector_store.count()
    return jsonify({
        'collection_name': vector_store.collection_name,
        'count': count
    })

@app.route('/api/list')
def list_embeddings():
    """List all embeddings."""
    limit = int(request.args.get('limit', 50))
    
    try:
        collection = vector_store.collection
        results = collection.get(
            limit=limit,
            include=["metadatas", "documents"]
        )
        
        items = []
        for i, uuid in enumerate(results["ids"]):
            metadata = results["metadatas"][i] if results["metadatas"] else {}
            document = results["documents"][i] if results["documents"] else ""
            
            items.append({
                'uuid': uuid,
                'subject': metadata.get('subject', 'N/A'),
                'sender': metadata.get('sender', 'N/A'),
                'date': metadata.get('date', 'N/A'),
                'preview': document[:200] if document else None,
                'recipients': 'N/A'  # Not stored in metadata
            })
        
        return jsonify({'items': items})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search_emails():
    """Search emails by email address."""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'items': []})
    
    db = SessionLocal()
    try:
        # Search in sender or recipients
        emails = db.query(Email).filter(
            (Email.sender.ilike(f"%{query}%")) |
            (Email.recipients.ilike(f"%{query}%"))
        ).limit(50).all()
        
        items = []
        for email in emails:
            recipients = json.loads(email.recipients) if email.recipients else []
            
            items.append({
                'uuid': email.id,
                'subject': email.subject,
                'sender': email.sender,
                'recipients': ', '.join(recipients),
                'date': email.date.isoformat() if email.date else 'N/A',
                'preview': email.body[:200] if email.body else None
            })
        
        return jsonify({'items': items})
    
    finally:
        db.close()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("ChromaDB Viewer Starting...")
    print("="*60)
    print("\nOpen your browser and go to: http://localhost:5001")
    print("\nPress Ctrl+C to stop the server\n")
    app.run(debug=True, port=5001)
