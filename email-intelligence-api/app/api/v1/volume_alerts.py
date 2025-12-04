"""Volume Alerts API endpoints - Form-based alerts for POC."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.volume_alert_service import VolumeAlertService
from app.schemas.volume_alert import (
    VolumeAlertCreate, VolumeAlertUpdate, VolumeAlertResponse,
    VolumeAlertListResponse, VolumeAlertTriggerResponse,
    AlertFormOptionsResponse
)

router = APIRouter()


# ============ Form UI ============

@router.get("/form", response_class=HTMLResponse)
def get_alert_form(db: Session = Depends(get_db)):
    """
    Serve the HTML form for creating volume alerts.
    """
    service = VolumeAlertService(db)
    entity_values = service.get_entity_values(limit=200)
    
    # Build entity options HTML
    entity_options = '<option value="">All entities of selected type</option>'
    for ev in entity_values:
        entity_options += f'<option value="{ev["value"]}" data-type="{ev["type"]}">{ev["value"]} ({ev["type"]}) - {ev["count"]} mentions</option>'
    
    html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Create Volume Alert</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0e14;
            --bg-secondary: #1a1f2e;
            --bg-card: #141924;
            --border-color: #2a3142;
            --text-primary: #e6e8eb;
            --text-secondary: #8b949e;
            --accent-cyan: #36d9c4;
            --accent-purple: #a78bfa;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --accent-green: #10b981;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            background-image: 
                radial-gradient(ellipse at 20% 20%, rgba(54, 217, 196, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(167, 139, 250, 0.06) 0%, transparent 50%);
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        
        .form-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        .form-section {{
            margin-bottom: 28px;
        }}
        
        .form-section-title {{
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--accent-cyan);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .form-section-title::before {{
            content: '';
            display: inline-block;
            width: 4px;
            height: 16px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 2px;
        }}
        
        .form-row {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 16px;
        }}
        
        .form-row.single {{
            grid-template-columns: 1fr;
        }}
        
        .form-group {{
            display: flex;
            flex-direction: column;
        }}
        
        label {{
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }}
        
        input, select, textarea {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            padding: 12px 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            transition: all 0.2s ease;
        }}
        
        input:focus, select:focus, textarea:focus {{
            outline: none;
            border-color: var(--accent-cyan);
            box-shadow: 0 0 0 3px rgba(54, 217, 196, 0.1);
        }}
        
        input::placeholder {{
            color: var(--text-secondary);
            opacity: 0.6;
        }}
        
        select {{
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238b949e' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 16px center;
            padding-right: 40px;
        }}
        
        .email-input-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 8px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            min-height: 50px;
        }}
        
        .email-tag {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: linear-gradient(135deg, rgba(54, 217, 196, 0.2), rgba(167, 139, 250, 0.2));
            border: 1px solid var(--accent-cyan);
            border-radius: 20px;
            font-size: 0.85rem;
            color: var(--accent-cyan);
        }}
        
        .email-tag button {{
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 1rem;
            line-height: 1;
            padding: 0;
        }}
        
        .email-tag button:hover {{
            color: var(--accent-red);
        }}
        
        .email-input {{
            flex: 1;
            min-width: 200px;
            border: none;
            background: transparent;
            padding: 6px;
        }}
        
        .email-input:focus {{
            box-shadow: none;
        }}
        
        .severity-options {{
            display: flex;
            gap: 12px;
        }}
        
        .severity-option {{
            flex: 1;
            position: relative;
        }}
        
        .severity-option input {{
            position: absolute;
            opacity: 0;
            pointer-events: none;
        }}
        
        .severity-option label {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 12px;
            background: var(--bg-secondary);
            border: 2px solid var(--border-color);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
            margin: 0;
        }}
        
        .severity-option input:checked + label {{
            border-color: var(--accent-cyan);
            background: rgba(54, 217, 196, 0.1);
        }}
        
        .severity-option.low label {{ color: var(--accent-green); }}
        .severity-option.medium label {{ color: var(--accent-orange); }}
        .severity-option.high label {{ color: #f97316; }}
        .severity-option.critical label {{ color: var(--accent-red); }}
        
        .toggle-container {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .toggle {{
            position: relative;
            width: 52px;
            height: 28px;
        }}
        
        .toggle input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        
        .toggle-slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--border-color);
            transition: 0.3s;
            border-radius: 28px;
        }}
        
        .toggle-slider::before {{
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 4px;
            bottom: 4px;
            background-color: var(--text-primary);
            transition: 0.3s;
            border-radius: 50%;
        }}
        
        .toggle input:checked + .toggle-slider {{
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
        }}
        
        .toggle input:checked + .toggle-slider::before {{
            transform: translateX(24px);
        }}
        
        .submit-btn {{
            width: 100%;
            padding: 16px 32px;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--bg-primary);
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }}
        
        .submit-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(54, 217, 196, 0.3);
        }}
        
        .submit-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        
        .alert-list {{
            margin-top: 40px;
        }}
        
        .alert-list h2 {{
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: var(--accent-purple);
        }}
        
        .alert-item {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .alert-item-info h3 {{
            font-size: 1.1rem;
            margin-bottom: 4px;
        }}
        
        .alert-item-info p {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .alert-item-actions {{
            display: flex;
            gap: 10px;
        }}
        
        .btn-small {{
            padding: 8px 16px;
            font-size: 0.85rem;
            border-radius: 6px;
            cursor: pointer;
            border: 1px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-primary);
            transition: all 0.2s;
        }}
        
        .btn-small:hover {{
            border-color: var(--accent-cyan);
        }}
        
        .btn-small.danger:hover {{
            border-color: var(--accent-red);
            color: var(--accent-red);
        }}
        
        .btn-small.evaluate {{
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: var(--bg-primary);
            border: none;
        }}
        
        .toast {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
            z-index: 1000;
        }}
        
        .toast.show {{
            opacity: 1;
            transform: translateY(0);
        }}
        
        .toast.success {{
            background: var(--accent-green);
        }}
        
        .toast.error {{
            background: var(--accent-red);
        }}
        
        @media (max-width: 640px) {{
            .form-row {{
                grid-template-columns: 1fr;
            }}
            
            .severity-options {{
                flex-wrap: wrap;
            }}
            
            .severity-option {{
                flex: 1 1 45%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Volume Alert</h1>
            <p>Monitor entity mention volumes and get notified when thresholds are exceeded</p>
        </div>
        
        <div class="form-card">
            <form id="alertForm">
                <!-- Alert Identification -->
                <div class="form-section">
                    <div class="form-section-title">Alert Details</div>
                    <div class="form-row single">
                        <div class="form-group">
                            <label for="name">Alert Name *</label>
                            <input type="text" id="name" name="name" required placeholder="e.g., High Volume PERSON Alert">
                        </div>
                    </div>
                    <div class="form-row single">
                        <div class="form-group">
                            <label for="description">Description</label>
                            <textarea id="description" name="description" rows="2" placeholder="Describe what this alert monitors..."></textarea>
                        </div>
                    </div>
                </div>
                
                <!-- Alert Configuration -->
                <div class="form-section">
                    <div class="form-section-title">Alert Configuration</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="alert_type">Alert Type</label>
                            <select id="alert_type" name="alert_type">
                                <option value="volume_spike">Volume Spike (% increase)</option>
                                <option value="volume_threshold">Volume Threshold (fixed count)</option>
                                <option value="volume_drop">Volume Drop (% decrease)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="file_format">File Format</label>
                            <select id="file_format" name="file_format">
                                <option value="all">All Formats</option>
                                <option value="csv">CSV Files</option>
                                <option value="eml">Email Files (.eml)</option>
                                <option value="pst">Outlook Files (.pst)</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <!-- Entity Configuration -->
                <div class="form-section">
                    <div class="form-section-title">Entity Configuration</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="entity_type">Entity Type</label>
                            <select id="entity_type" name="entity_type">
                                <option value="ALL">All Entities</option>
                                <option value="PERSON">Person</option>
                                <option value="ORG">Organization</option>
                                <option value="GPE">Location</option>
                                <option value="MONEY">Money</option>
                                <option value="DATE">Date</option>
                                <option value="PRODUCT">Product</option>
                                <option value="EVENT">Event</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="entity_value">Specific Entity (optional)</label>
                            <select id="entity_value" name="entity_value">
                                {entity_options}
                            </select>
                        </div>
                    </div>
                </div>
                
                <!-- Threshold Configuration -->
                <div class="form-section">
                    <div class="form-section-title">Threshold Settings</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="threshold_value">Threshold Value</label>
                            <input type="number" id="threshold_value" name="threshold_value" value="50" min="1" max="1000">
                        </div>
                        <div class="form-group">
                            <label for="threshold_type">Threshold Type</label>
                            <select id="threshold_type" name="threshold_type">
                                <option value="percentage">Percentage</option>
                                <option value="absolute">Absolute Count</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="duration">Monitoring Duration</label>
                            <select id="duration" name="duration">
                                <option value="1_day">1 Day</option>
                                <option value="2_days">2 Days</option>
                                <option value="3_days">3 Days</option>
                                <option value="7_days">7 Days</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <!-- Notification Settings -->
                <div class="form-section">
                    <div class="form-section-title">Notification Settings</div>
                    <div class="form-row single">
                        <div class="form-group">
                            <label>Subscriber Emails</label>
                            <div class="email-input-container" id="emailContainer">
                                <input type="email" class="email-input" id="emailInput" placeholder="Enter email and press Enter...">
                            </div>
                            <input type="hidden" id="subscriber_emails" name="subscriber_emails">
                        </div>
                    </div>
                </div>
                
                <!-- Severity -->
                <div class="form-section">
                    <div class="form-section-title">Severity Level</div>
                    <div class="severity-options">
                        <div class="severity-option low">
                            <input type="radio" id="severity_low" name="severity" value="low">
                            <label for="severity_low">Low</label>
                        </div>
                        <div class="severity-option medium">
                            <input type="radio" id="severity_medium" name="severity" value="medium" checked>
                            <label for="severity_medium">Medium</label>
                        </div>
                        <div class="severity-option high">
                            <input type="radio" id="severity_high" name="severity" value="high">
                            <label for="severity_high">High</label>
                        </div>
                        <div class="severity-option critical">
                            <input type="radio" id="severity_critical" name="severity" value="critical">
                            <label for="severity_critical">Critical</label>
                        </div>
                    </div>
                </div>
                
                <!-- Enable Toggle -->
                <div class="form-section">
                    <div class="toggle-container">
                        <label class="toggle">
                            <input type="checkbox" id="enabled" name="enabled" checked>
                            <span class="toggle-slider"></span>
                        </label>
                        <span>Enable Alert</span>
                    </div>
                </div>
                
                <button type="submit" class="submit-btn" id="submitBtn">Create Alert</button>
            </form>
        </div>
        
        <!-- Existing Alerts List -->
        <div class="alert-list" id="alertList">
            <h2>📋 Existing Alerts</h2>
            <div id="alertsContainer">Loading...</div>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        // Email tags handling
        const emails = [];
        const emailInput = document.getElementById('emailInput');
        const emailContainer = document.getElementById('emailContainer');
        const subscriberEmailsInput = document.getElementById('subscriber_emails');
        
        emailInput.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') {{
                e.preventDefault();
                const email = this.value.trim();
                if (email && isValidEmail(email) && !emails.includes(email)) {{
                    emails.push(email);
                    renderEmails();
                    this.value = '';
                }}
            }}
        }});
        
        function isValidEmail(email) {{
            return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email);
        }}
        
        function renderEmails() {{
            const tags = emails.map((email, index) => `
                <span class="email-tag">
                    ${{email}}
                    <button type="button" onclick="removeEmail(${{index}})">&times;</button>
                </span>
            `).join('');
            
            emailContainer.innerHTML = tags + '<input type="email" class="email-input" id="emailInput" placeholder="Enter email and press Enter...">';
            
            // Rebind the input
            const newInput = document.getElementById('emailInput');
            newInput.addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') {{
                    e.preventDefault();
                    const email = this.value.trim();
                    if (email && isValidEmail(email) && !emails.includes(email)) {{
                        emails.push(email);
                        renderEmails();
                    }}
                }}
            }});
            
            subscriberEmailsInput.value = JSON.stringify(emails);
        }}
        
        function removeEmail(index) {{
            emails.splice(index, 1);
            renderEmails();
        }}
        
        // Form submission
        document.getElementById('alertForm').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating...';
            
            const formData = {{
                name: document.getElementById('name').value,
                description: document.getElementById('description').value || null,
                alert_type: document.getElementById('alert_type').value,
                file_format: document.getElementById('file_format').value,
                entity_type: document.getElementById('entity_type').value,
                entity_value: document.getElementById('entity_value').value || null,
                threshold_value: parseInt(document.getElementById('threshold_value').value),
                threshold_type: document.getElementById('threshold_type').value,
                duration: document.getElementById('duration').value,
                subscriber_emails: emails,
                severity: document.querySelector('input[name="severity"]:checked').value,
                enabled: document.getElementById('enabled').checked
            }};
            
            try {{
                const response = await fetch('/api/v1/volume-alerts', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify(formData)
                }});
                
                if (response.ok) {{
                    const result = await response.json();
                    showToast('Alert created successfully!', 'success');
                    document.getElementById('alertForm').reset();
                    emails.length = 0;
                    renderEmails();
                    loadAlerts();
                }} else {{
                    const error = await response.json();
                    showToast(error.detail || 'Failed to create alert', 'error');
                }}
            }} catch (err) {{
                showToast('Network error: ' + err.message, 'error');
            }} finally {{
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create Alert';
            }}
        }});
        
        // Toast notification
        function showToast(message, type) {{
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type + ' show';
            
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 3000);
        }}
        
        // Load existing alerts
        async function loadAlerts() {{
            try {{
                const response = await fetch('/api/v1/volume-alerts');
                const data = await response.json();
                
                const container = document.getElementById('alertsContainer');
                
                if (data.alerts.length === 0) {{
                    container.innerHTML = '<p style="color: var(--text-secondary);">No alerts created yet.</p>';
                    return;
                }}
                
                container.innerHTML = data.alerts.map(alert => `
                    <div class="alert-item">
                        <div class="alert-item-info">
                            <h3>${{alert.name}}</h3>
                            <p>${{alert.entity_type}} | ${{alert.alert_type}} | ${{alert.duration}} | ${{alert.severity}}</p>
                        </div>
                        <div class="alert-item-actions">
                            <button class="btn-small evaluate" onclick="evaluateAlert('${{alert.id}}')">Evaluate</button>
                            <button class="btn-small danger" onclick="deleteAlert('${{alert.id}}')">Delete</button>
                        </div>
                    </div>
                `).join('');
            }} catch (err) {{
                document.getElementById('alertsContainer').innerHTML = '<p style="color: var(--accent-red);">Failed to load alerts</p>';
            }}
        }}
        
        async function evaluateAlert(id) {{
            try {{
                const response = await fetch(`/api/v1/volume-alerts/${{id}}/evaluate`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.triggered) {{
                    showToast(`Alert triggered! ${{result.trigger_reason}}`, 'success');
                }} else {{
                    showToast(`Alert not triggered. Current volume: ${{result.current_volume}}`, 'success');
                }}
            }} catch (err) {{
                showToast('Failed to evaluate alert', 'error');
            }}
        }}
        
        async function deleteAlert(id) {{
            if (!confirm('Are you sure you want to delete this alert?')) return;
            
            try {{
                const response = await fetch(`/api/v1/volume-alerts/${{id}}`, {{
                    method: 'DELETE'
                }});
                
                if (response.ok) {{
                    showToast('Alert deleted', 'success');
                    loadAlerts();
                }} else {{
                    showToast('Failed to delete alert', 'error');
                }}
            }} catch (err) {{
                showToast('Network error', 'error');
            }}
        }}
        
        // Filter entity values based on type selection
        document.getElementById('entity_type').addEventListener('change', function() {{
            const selectedType = this.value;
            const entityValueSelect = document.getElementById('entity_value');
            const options = entityValueSelect.options;
            
            for (let i = 0; i < options.length; i++) {{
                const option = options[i];
                const optionType = option.dataset.type;
                
                if (!optionType || selectedType === 'ALL' || optionType === selectedType) {{
                    option.style.display = '';
                }} else {{
                    option.style.display = 'none';
                }}
            }}
            
            entityValueSelect.value = '';
        }});
        
        // Load alerts on page load
        loadAlerts();
    </script>
</body>
</html>
    '''
    return HTMLResponse(content=html_content)


# ============ Form Options ============

@router.get("/options", response_model=AlertFormOptionsResponse)
def get_form_options():
    """Get available options for the alert creation form."""
    return AlertFormOptionsResponse()


@router.get("/entity-values")
def get_entity_values(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get available entity values for the entity dropdown."""
    service = VolumeAlertService(db)
    values = service.get_entity_values(entity_type=entity_type, limit=limit)
    
    return {
        "total": len(values),
        "entity_values": values
    }


# ============ Volume Alert CRUD ============

@router.get("", response_model=VolumeAlertListResponse)
def list_volume_alerts(
    enabled_only: bool = Query(False, description="Only return enabled alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List all volume alerts."""
    service = VolumeAlertService(db)
    alerts, total = service.list(
        enabled_only=enabled_only,
        alert_type=alert_type,
        limit=limit
    )
    
    return VolumeAlertListResponse(
        total=total,
        alerts=[VolumeAlertResponse.model_validate(a) for a in alerts]
    )


@router.post("", response_model=VolumeAlertResponse)
def create_volume_alert(
    data: VolumeAlertCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new volume-based alert.
    
    ## Alert Types
    
    - **volume_spike**: Trigger when entity mentions exceed baseline by threshold percentage
    - **volume_threshold**: Trigger when mentions exceed a fixed count
    - **volume_drop**: Trigger when mentions drop below baseline by threshold percentage
    
    ## Example
    ```json
    {
      "name": "High PERSON Volume Alert",
      "alert_type": "volume_spike",
      "entity_type": "PERSON",
      "threshold_value": 50,
      "threshold_type": "percentage",
      "duration": "1_day",
      "subscriber_emails": ["analyst@company.com"],
      "severity": "high"
    }
    ```
    """
    service = VolumeAlertService(db)
    
    # Check for duplicate name
    existing = service.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Alert with this name already exists")
    
    alert = service.create(data)
    return VolumeAlertResponse.model_validate(alert)


@router.get("/{alert_id}", response_model=VolumeAlertResponse)
def get_volume_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific volume alert by ID."""
    service = VolumeAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Volume alert not found")
    
    return VolumeAlertResponse.model_validate(alert)


@router.put("/{alert_id}", response_model=VolumeAlertResponse)
def update_volume_alert(
    alert_id: str,
    data: VolumeAlertUpdate,
    db: Session = Depends(get_db)
):
    """Update a volume alert."""
    service = VolumeAlertService(db)
    alert = service.update(alert_id, data)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Volume alert not found")
    
    return VolumeAlertResponse.model_validate(alert)


@router.delete("/{alert_id}")
def delete_volume_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete a volume alert."""
    service = VolumeAlertService(db)
    success = service.delete(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Volume alert not found")
    
    return {"message": "Volume alert deleted successfully"}


# ============ Alert Evaluation ============

@router.post("/{alert_id}/evaluate", response_model=VolumeAlertTriggerResponse)
def evaluate_alert(alert_id: str, db: Session = Depends(get_db)):
    """
    Manually evaluate a specific alert.
    
    Returns whether the alert would trigger based on current data.
    """
    service = VolumeAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Volume alert not found")
    
    triggered, matched_data = service.evaluate(alert)
    
    return VolumeAlertTriggerResponse(
        alert_id=alert_id,
        alert_name=alert.name,
        triggered=triggered,
        trigger_reason=matched_data.get("trigger_reason"),
        current_volume=matched_data.get("current_volume", 0),
        baseline_volume=matched_data.get("baseline_volume", 0),
        change_percentage=matched_data.get("change_percentage", 0.0),
        matched_entities=matched_data.get("matched_entities", [])
    )


@router.post("/evaluate-all")
def evaluate_all_alerts(db: Session = Depends(get_db)):
    """Evaluate all enabled volume alerts."""
    service = VolumeAlertService(db)
    triggered = service.evaluate_all()
    
    return {
        "evaluated": True,
        "triggered_count": len(triggered),
        "triggered_alerts": triggered
    }


# ============ Alert History ============

@router.get("/triggered/all")
def get_all_triggered_alerts(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all recently triggered volume alerts."""
    service = VolumeAlertService(db)
    triggered = service.get_triggered_alerts(limit=limit)
    
    return {
        "total": len(triggered),
        "triggered": triggered
    }

