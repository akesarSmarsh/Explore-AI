---
name: Email Intelligence API - Implementation Plan
overview: ""
todos:
  - id: 8783d21e-02c1-4de4-b767-05528b3a6729
    content: Create project structure, dependencies, and FastAPI boilerplate with SQLite + ChromaDB setup
    status: pending
  - id: 4c8da69e-b3f4-4c47-bf6c-b793dbb147d2
    content: "Build data pipeline: download Enron sample, parse emails, run NER, generate embeddings"
    status: pending
  - id: 36b64341-fd87-4327-bd27-e22ca37d6c06
    content: Implement email endpoints with filtering, pagination, and entity highlighting
    status: pending
  - id: 82d7f84d-d71e-4ba4-bef5-a65070f23f80
    content: "Implement entity endpoints: listing, types, statistics, co-occurrences"
    status: pending
  - id: 814f781b-fabd-4eaf-8053-8e9ab22203b6
    content: Implement semantic search, similar emails, and keyword search endpoints
    status: pending
  - id: bc26c464-4d22-458c-92b9-799addaa6312
    content: Implement alert rules CRUD and alert evaluation engine with 6 rule types
    status: pending
  - id: 3b4fd507-62f8-4923-a788-8fdd293e1834
    content: "Implement analytics endpoints: overview, timeline, top-senders, entity-network"
    status: pending
  - id: 19c4f6cc-8f84-47da-ad9b-1254bd2f4a20
    content: Create Dockerfile, docker-compose.yml, and README documentation
    status: pending
---

# Email Intelligence API - Implementation Plan

## Tech Stack

- **API**: FastAPI with async support
- **Databases**: SQLite (structured data) + ChromaDB (vectors)
- **NER**: spaCy (en_core_web_sm or en_core_web_trf)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Containerization**: Docker + docker-compose

---

## Database Schema (SQLite)

### Tables

```sql
-- emails
id, message_id, subject, sender, recipients, cc, date, body, raw_file_path, created_at

-- entities  
id, email_id, text, type, start_pos, end_pos, sentence, created_at

-- alert_rules
id, name, description, severity, enabled, conditions (JSON), created_at

-- alerts
id, rule_id, email_id, entity_id, severity, status, matched_text, context, triggered_at
```

### ChromaDB Collections

- `email_embeddings` - Full email body embeddings for semantic search

---

## API Endpoints Summary

| Group | Endpoints |

|-------|-----------|

| Emails | GET/POST /emails, GET /emails/{id} |

| Entities | GET /entities, GET /entities/types, GET /entities/co-occurrences |

| Search | POST /search/semantic, POST /search/similar, GET /search/keyword |

| Alerts | CRUD /alerts, CRUD /alerts/rules, POST /alerts/rules/{id}/test |

| Analytics | GET /analytics/overview, timeline, top-senders, entity-network |

---

## Implementation Phases

### Phase 1: Project Setup

- Create project structure with FastAPI boilerplate
- Set up SQLite with SQLAlchemy ORM
- Set up ChromaDB client
- Create requirements.txt and Dockerfile

### Phase 2: Data Pipeline

- Download Enron sample dataset (~10K emails)
- Parse email files (extract metadata + body)
- Run spaCy NER on all emails
- Generate embeddings and store in ChromaDB
- Populate SQLite with emails and entities

### Phase 3: Core API Endpoints

- Implement email CRUD with filtering/pagination
- Implement entity listing and statistics
- Implement semantic search and similar email search
- Implement keyword search with SQLite FTS5

### Phase 4: Smart Alerts System

- Implement alert rule CRUD
- Build alert evaluation engine (6 rule types)
- Create alert triggering on email processing
- Implement alert management (acknowledge, dismiss)

### Phase 5: Analytics Endpoints

- Dashboard overview statistics
- Timeline data for entity mentions
- Top senders analysis
- Entity co-occurrence network data

### Phase 6: Docker & Documentation

- Create docker-compose.yml
- Write API documentation
- Create sample .env and README

---

## Key Files to Create

```
email-intelligence-api/
├── app/
│   ├── main.py              # FastAPI entry
│   ├── config.py            # Settings with pydantic
│   ├── database.py          # SQLite + ChromaDB setup
│   ├── api/v1/              # All route handlers
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── core/                # NER, embeddings, vector store
├── scripts/
│   ├── download_data.py     # Download Enron sample
│   └── process_emails.py    # Initial data processing
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Default Alert Rules (Pre-seeded)

1. **High Value Transaction**: MONEY > $1,000,000
2. **Regulatory Mention**: ORG contains SEC, FBI, DOJ
3. **Executive Mention**: PERSON in [Ken Lay, Jeff Skilling, Andrew Fastow]
4. **Sensitive Keywords**: Keywords [fraud, illegal, destroy, shred] + any PERSON
5. **High Entity Density**: >10 entities in single email