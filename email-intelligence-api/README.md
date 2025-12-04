# Email Intelligence API

A FastAPI backend for email analysis using NER (Named Entity Recognition), semantic search, smart alerts with anomaly detection, and email notifications.

## Features

- **Named Entity Recognition (NER)**: Extract people, organizations, locations, money, dates, emails, and phone numbers
- **Word Cloud Visualization**: API for word cloud data with entity frequencies
- **Semantic Search**: Natural language search using AI embeddings
- **Smart Alerts**: Customizable rules with anomaly detection
- **Anomaly Detection**: Volume spike, sudden appearance, and frequency change detection
- **Email Notifications**: SMTP-based alert notifications
- **Background Scheduler**: Automated alert checking (hourly, daily, weekly)
- **Dashboard APIs**: Summary statistics and activity feeds

## Tech Stack

- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database for structured data
- **ChromaDB**: Vector database for semantic search
- **spaCy**: NLP library for entity extraction
- **Sentence Transformers**: AI embeddings for semantic search
- **APScheduler**: Background job scheduling

## Quick Start

### 1. Install Dependencies

```bash
cd email-intelligence-api
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Start the Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Access the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### NER Visualization (Tab 1)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ner/wordcloud` | GET | Word cloud data with filters |
| `/api/v1/ner/breakdown` | GET | Entity breakdown by type |
| `/api/v1/ner/trending` | GET | Trending entities over time |
| `/api/v1/ner/top-entities` | GET | Top entities with statistics |
| `/api/v1/ner/baseline/{type}` | GET | Baseline stats for anomaly config |

### Dashboard / Search (Tab 2)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/dashboard/summary` | GET | Dashboard summary stats |
| `/api/v1/dashboard/activity` | GET | Recent activity feed |
| `/api/v1/search/semantic` | POST | Semantic search |
| `/api/v1/search/similar` | POST | Find similar emails |
| `/api/v1/search/keyword` | GET | Keyword search |

### Smart Alerts (Tab 3)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/smart-alerts` | GET | List all smart alerts |
| `/api/v1/smart-alerts` | POST | Create new smart alert |
| `/api/v1/smart-alerts/{id}` | GET | Get alert details |
| `/api/v1/smart-alerts/{id}` | PUT | Update smart alert |
| `/api/v1/smart-alerts/{id}` | DELETE | Delete smart alert |
| `/api/v1/smart-alerts/{id}/evaluate` | POST | Manually evaluate alert |
| `/api/v1/smart-alerts/{id}/test` | POST | Test alert against sample |
| `/api/v1/smart-alerts/{id}/history` | GET | Get alert trigger history |
| `/api/v1/smart-alerts/evaluate-all` | POST | Evaluate all enabled alerts |
| `/api/v1/smart-alerts/triggered/all` | GET | Get all triggered alerts |

## Smart Alert Types

### Standard Alerts

1. **entity_threshold** - Entity value exceeds threshold (e.g., MONEY > $1M)
2. **entity_mention** - Specific entities mentioned
3. **keyword_match** - Keywords detected in email
4. **co_occurrence** - Two entity types appear together
5. **pattern_match** - Regex pattern matches

### Anomaly Detection Alerts

6. **volume_spike** - Entity mentions exceed baseline during time window
7. **sudden_appearance** - New entity appears not seen in baseline period
8. **frequency_change** - Significant change in entity mention frequency

## Example: Creating an Anomaly Alert

```json
POST /api/v1/smart-alerts
{
  "name": "PERSON Volume Spike Alert",
  "description": "Alert when PERSON mentions spike above baseline",
  "alert_type": "volume_spike",
  "anomaly_config": {
    "entity_type": "PERSON",
    "monitoring_window": {"duration": 24, "unit": "hours"},
    "baseline_period": {"duration": 7, "unit": "days"},
    "threshold": {"type": "percentage", "value": 50},
    "min_baseline_count": 10
  },
  "schedule": {
    "type": "scheduled",
    "frequency": "hourly"
  },
  "notifications": {
    "email": {
      "enabled": true,
      "recipients": ["admin@company.com"],
      "subject_template": "Alert: {{alert_name}} triggered"
    }
  },
  "severity": "high",
  "enabled": true
}
```

### Threshold Types

- **percentage**: Alert if X% above baseline (e.g., 50% increase)
- **multiplier**: Alert if X times baseline (e.g., 2x)
- **std_deviation**: Alert if X standard deviations above mean
- **absolute**: Alert if count exceeds fixed number

## Email Notifications

Configure SMTP in `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=alerts@yourdomain.com
```

## Background Scheduler

The scheduler automatically runs:
- **Hourly**: Alerts with `frequency: "hourly"`
- **Daily (9 AM)**: Alerts with `frequency: "daily"`
- **Weekly (Monday 9 AM)**: Alerts with `frequency: "weekly"`

Disable scheduler in `.env`:
```env
ENABLE_SCHEDULER=false
```

## Project Structure

```
email-intelligence-api/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration
│   ├── database.py                # Database connections
│   ├── api/v1/
│   │   ├── emails.py              # Email CRUD
│   │   ├── entities.py            # Entity endpoints
│   │   ├── search.py              # Search endpoints
│   │   ├── ner.py                 # NER visualization
│   │   ├── smart_alerts.py        # Smart alerts CRUD
│   │   ├── dashboard.py           # Dashboard summary
│   │   ├── analytics.py           # Analytics
│   │   └── system.py              # System endpoints
│   ├── models/
│   │   ├── email.py
│   │   ├── entity.py
│   │   ├── alert.py
│   │   └── smart_alert.py         # Smart alerts & history
│   ├── schemas/
│   │   ├── ner.py                 # NER schemas
│   │   └── smart_alert.py         # Smart alert schemas
│   ├── services/
│   │   ├── email_service.py
│   │   ├── entity_service.py
│   │   ├── search_service.py
│   │   ├── ner_analytics_service.py   # Word cloud logic
│   │   ├── smart_alert_service.py     # Smart alert logic
│   │   ├── anomaly_service.py         # Anomaly detection
│   │   ├── notification_service.py    # Email sending
│   │   └── scheduler_service.py       # Background jobs
│   └── core/
│       ├── ner_processor.py
│       ├── embeddings.py
│       └── vector_store.py
├── scripts/
│   ├── download_data.py
│   └── process_emails.py
├── data/
│   ├── emails.db                  # SQLite database
│   └── chroma/                    # Vector database
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Docker Deployment

```bash
docker-compose up -d
```

## License

MIT License
