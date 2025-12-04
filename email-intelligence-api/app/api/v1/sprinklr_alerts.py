"""Sprinklr-style Alerts API endpoints with comprehensive form UI."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.sprinklr_alert_service import SprinklrAlertService
from app.schemas.sprinklr_alert import (
    SprinklrAlertCreate, SprinklrAlertUpdate, SprinklrAlertResponse,
    SprinklrAlertListResponse, EvaluationResult, SprinklrFormOptionsResponse
)

router = APIRouter()


# ============ Form UI ============

@router.get("/form", response_class=HTMLResponse)
def get_alert_form(db: Session = Depends(get_db)):
    """Serve the comprehensive Sprinklr-style alert creation form."""
    
    html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sprinklr-Style Alert Manager</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f1419;
            --bg-card: #1a1f2e;
            --bg-input: #242b3d;
            --border: #2d3548;
            --border-focus: #3b82f6;
            --text: #e2e8f0;
            --text-muted: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
            --accent-orange: #f97316;
            --accent-red: #ef4444;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            background-image: 
                radial-gradient(ellipse at 0% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 100% 100%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px 24px;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
        }
        
        .header h1 {
            font-size: 1.75rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .header h1 span {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
        }
        
        .tab {
            padding: 12px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-muted);
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .tab:hover { border-color: var(--accent-blue); color: var(--text); }
        .tab.active { 
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
            border-color: var(--accent-blue);
            color: var(--text);
        }
        
        .layout {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 24px;
        }
        
        @media (max-width: 1024px) {
            .layout { grid-template-columns: 1fr; }
        }
        
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
        }
        
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--accent-cyan);
        }
        
        .form-section {
            margin-bottom: 28px;
        }
        
        .section-title {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }
        
        .form-row {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 16px;
        }
        
        .form-row.single { grid-template-columns: 1fr; }
        .form-row.triple { grid-template-columns: repeat(3, 1fr); }
        
        .form-group { display: flex; flex-direction: column; }
        
        .form-group label {
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-muted);
            margin-bottom: 8px;
        }
        
        input, select, textarea {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            padding: 10px 14px;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text);
            transition: all 0.2s;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }
        
        select {
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            padding-right: 36px;
        }
        
        .alert-type-cards {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        
        .alert-type-card {
            padding: 16px;
            background: var(--bg-input);
            border: 2px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .alert-type-card:hover { border-color: var(--accent-blue); }
        .alert-type-card.selected {
            border-color: var(--accent-blue);
            background: rgba(59, 130, 246, 0.1);
        }
        
        .alert-type-card h4 { font-size: 0.95rem; margin-bottom: 4px; }
        .alert-type-card p { font-size: 0.8rem; color: var(--text-muted); }
        
        .toggle-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        
        .toggle-row:last-child { border-bottom: none; }
        
        .toggle {
            position: relative;
            width: 44px;
            height: 24px;
        }
        
        .toggle input { opacity: 0; width: 0; height: 0; }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            inset: 0;
            background: var(--border);
            border-radius: 24px;
            transition: 0.3s;
        }
        
        .toggle-slider::before {
            content: "";
            position: absolute;
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background: var(--text);
            border-radius: 50%;
            transition: 0.3s;
        }
        
        .toggle input:checked + .toggle-slider { background: var(--accent-blue); }
        .toggle input:checked + .toggle-slider::before { transform: translateX(20px); }
        
        .severity-pills {
            display: flex;
            gap: 8px;
        }
        
        .severity-pill {
            flex: 1;
            padding: 10px;
            text-align: center;
            border: 2px solid var(--border);
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        
        .severity-pill.low { color: var(--accent-green); }
        .severity-pill.medium { color: var(--accent-yellow); }
        .severity-pill.high { color: var(--accent-orange); }
        .severity-pill.critical { color: var(--accent-red); }
        
        .severity-pill.selected {
            border-color: currentColor;
            background: rgba(255,255,255,0.05);
        }
        
        .email-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 10px;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 6px;
            min-height: 44px;
        }
        
        .email-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: rgba(59, 130, 246, 0.2);
            border: 1px solid var(--accent-blue);
            border-radius: 16px;
            font-size: 0.8rem;
            color: var(--accent-blue);
        }
        
        .email-tag button {
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            font-size: 1rem;
            line-height: 1;
        }
        
        .email-input {
            flex: 1;
            min-width: 180px;
            border: none;
            background: transparent;
            padding: 4px;
        }
        
        .btn {
            padding: 12px 24px;
            font-family: inherit;
            font-size: 0.95rem;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            color: white;
            width: 100%;
        }
        
        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
        }
        
        .btn-sm {
            padding: 8px 14px;
            font-size: 0.85rem;
        }
        
        .btn-outline {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
        }
        
        .btn-outline:hover { border-color: var(--accent-blue); }
        
        .btn-danger { border-color: var(--accent-red); color: var(--accent-red); }
        .btn-danger:hover { background: rgba(239, 68, 68, 0.1); }
        
        .alert-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .alert-item {
            padding: 16px;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        
        .alert-item-info h4 { font-size: 0.95rem; margin-bottom: 4px; }
        .alert-item-info p { font-size: 0.8rem; color: var(--text-muted); }
        
        .alert-item-meta {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }
        
        .meta-tag {
            font-size: 0.7rem;
            padding: 3px 8px;
            background: rgba(255,255,255,0.05);
            border-radius: 4px;
            color: var(--text-muted);
        }
        
        .alert-item-actions {
            display: flex;
            gap: 8px;
        }
        
        .conditional-section {
            display: none;
            animation: fadeIn 0.2s ease;
        }
        
        .conditional-section.visible { display: block; }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 14px 20px;
            border-radius: 8px;
            font-weight: 500;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s;
            z-index: 1000;
        }
        
        .toast.show { opacity: 1; transform: translateY(0); }
        .toast.success { background: var(--accent-green); color: white; }
        .toast.error { background: var(--accent-red); color: white; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            padding: 16px;
            background: var(--bg-input);
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-card .value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent-blue);
        }
        
        .stat-card .label {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 4px;
        }
        
        .keywords-input {
            display: flex;
            gap: 8px;
        }
        
        .keywords-input input { flex: 1; }
        
        .keyword-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        
        .keyword-tag {
            padding: 4px 10px;
            background: rgba(139, 92, 246, 0.2);
            border: 1px solid var(--accent-purple);
            border-radius: 4px;
            font-size: 0.8rem;
            color: var(--accent-purple);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .keyword-tag button {
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
        }
        
        .help-text {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 <span>Alert Manager</span></h1>
            <button class="btn btn-outline btn-sm" onclick="loadStats()">↻ Refresh</button>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('create')">Create Alert</div>
            <div class="tab" onclick="showTab('manage')">Manage Alerts</div>
            <div class="tab" onclick="showTab('history')">Trigger History</div>
        </div>
        
        <div id="createTab" class="layout">
            <!-- Form Card -->
            <div class="card">
                <form id="alertForm">
                    <!-- Basic Info -->
                    <div class="form-section">
                        <div class="section-title">Basic Information</div>
                        <div class="form-row single">
                            <div class="form-group">
                                <label>Alert Name *</label>
                                <input type="text" id="name" required placeholder="e.g., High Volume Person Mentions">
                            </div>
                        </div>
                        <div class="form-row single">
                            <div class="form-group">
                                <label>Description</label>
                                <textarea id="description" rows="2" placeholder="Describe what this alert monitors..."></textarea>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Alert Type -->
                    <div class="form-section">
                        <div class="section-title">Alert Type</div>
                        <div class="alert-type-cards">
                            <div class="alert-type-card selected" data-type="static" onclick="selectAlertType('static')">
                                <h4>📊 Static Threshold</h4>
                                <p>Trigger when metric exceeds a fixed value</p>
                            </div>
                            <div class="alert-type-card" data-type="smart" onclick="selectAlertType('smart')">
                                <h4>🧠 Smart Alert (AI)</h4>
                                <p>Detect anomalies using statistical analysis</p>
                            </div>
                        </div>
                        <input type="hidden" id="alert_type" value="static">
                    </div>
                    
                    <!-- Metric Configuration -->
                    <div class="form-section">
                        <div class="section-title">Metric to Monitor</div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Metric Type</label>
                                <select id="metric_type" onchange="updateMetricOptions()">
                                    <option value="email_volume">Email Volume</option>
                                    <option value="unique_senders">Unique Senders</option>
                                    <option value="entity_mentions">Entity Mentions</option>
                                    <option value="keyword_matches">Keyword Matches</option>
                                </select>
                            </div>
                            <div class="form-group" id="entityTypeGroup">
                                <label>Entity Type</label>
                                <select id="entity_type">
                                    <option value="ALL">All Entities</option>
                                    <option value="PERSON">Person</option>
                                    <option value="ORG">Organization</option>
                                    <option value="GPE">Location</option>
                                    <option value="MONEY">Money</option>
                                    <option value="DATE">Date</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row single" id="entityValueGroup">
                            <div class="form-group">
                                <label>Specific Entity (optional)</label>
                                <input type="text" id="entity_value" placeholder="e.g., Ken Lay, Enron">
                                <div class="help-text">Leave empty to monitor all entities of the selected type</div>
                            </div>
                        </div>
                        <div class="form-row single conditional-section" id="keywordsGroup">
                            <div class="form-group">
                                <label>Keywords to Monitor</label>
                                <div class="keywords-input">
                                    <input type="text" id="keywordInput" placeholder="Enter keyword and press Enter">
                                    <button type="button" class="btn btn-outline btn-sm" onclick="addKeyword()">Add</button>
                                </div>
                                <div class="keyword-list" id="keywordList"></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Time Window -->
                    <div class="form-section">
                        <div class="section-title">Time Window</div>
                        <div class="form-row triple">
                            <div class="form-group">
                                <label>Window Size</label>
                                <input type="number" id="window_size" value="1" min="1" max="30">
                            </div>
                            <div class="form-group">
                                <label>Unit</label>
                                <select id="window_unit">
                                    <option value="hours">Hours</option>
                                    <option value="days" selected>Days</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Check Every (min)</label>
                                <input type="number" id="check_frequency" value="60" min="5" max="1440">
                            </div>
                        </div>
                        <div class="form-row single conditional-section" id="baselineGroup">
                            <div class="form-group">
                                <label>Baseline Period (days)</label>
                                <input type="number" id="baseline_days" value="7" min="1" max="90">
                                <div class="help-text">Historical data used to calculate normal patterns</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Static Threshold (conditional) -->
                    <div class="form-section conditional-section visible" id="thresholdSection">
                        <div class="section-title">Threshold Settings</div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Operator</label>
                                <select id="operator">
                                    <option value="greater_than">> Greater than</option>
                                    <option value="less_than">< Less than</option>
                                    <option value="equals">= Equals</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Value</label>
                                <input type="number" id="threshold_value" value="100" min="0">
                            </div>
                        </div>
                    </div>
                    
                    <!-- Smart Alert Settings (conditional) -->
                    <div class="form-section conditional-section" id="anomalySection">
                        <div class="section-title">Anomaly Detection Settings</div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Algorithm</label>
                                <select id="algorithm">
                                    <option value="zscore">Z-Score (Statistical)</option>
                                    <option value="ewma">EWMA (Trend-based)</option>
                                    <option value="percentage_change">% Change</option>
                                </select>
                            </div>
                            <div class="form-group" id="zscoreThresholdGroup">
                                <label>Z-Score Threshold</label>
                                <input type="number" id="zscore_threshold" value="2.5" min="1" max="5" step="0.1">
                                <div class="help-text">2.5 = ~99% confidence anomaly</div>
                            </div>
                        </div>
                        <div class="form-row single conditional-section" id="pctChangeGroup">
                            <div class="form-group">
                                <label>Percentage Change Threshold (%)</label>
                                <input type="number" id="percentage_threshold" value="50" min="10" max="500">
                            </div>
                        </div>
                    </div>
                    
                    <!-- Anti-Spam / Cooldown -->
                    <div class="form-section">
                        <div class="section-title">Anti-Spam Controls</div>
                        <div class="toggle-row">
                            <span>Enable Cooldown</span>
                            <label class="toggle">
                                <input type="checkbox" id="cooldown_enabled" checked>
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="form-row triple" style="margin-top: 16px;">
                            <div class="form-group">
                                <label>Cooldown (minutes)</label>
                                <input type="number" id="cooldown_minutes" value="60" min="5" max="1440">
                            </div>
                            <div class="form-group">
                                <label>Max Alerts/Day</label>
                                <input type="number" id="max_alerts_per_day" value="10" min="1" max="100">
                            </div>
                            <div class="form-group">
                                <label>Consecutive Required</label>
                                <input type="number" id="consecutive_anomalies" value="1" min="1" max="10">
                            </div>
                        </div>
                    </div>
                    
                    <!-- Notifications -->
                    <div class="form-section">
                        <div class="section-title">Notifications</div>
                        <div class="toggle-row">
                            <span>Email Notifications</span>
                            <label class="toggle">
                                <input type="checkbox" id="email_enabled" checked>
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="form-row single" style="margin-top: 16px;">
                            <div class="form-group">
                                <label>Recipient Emails</label>
                                <div class="email-tags" id="emailContainer">
                                    <input type="email" class="email-input" id="emailInput" placeholder="Enter email and press Enter">
                                </div>
                            </div>
                        </div>
                        <div class="toggle-row">
                            <span>Dashboard Indicator</span>
                            <label class="toggle">
                                <input type="checkbox" id="dashboard_enabled" checked>
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="toggle-row">
                            <span>Webhook (Slack/Teams)</span>
                            <label class="toggle">
                                <input type="checkbox" id="webhook_enabled">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="form-row single conditional-section" id="webhookUrlGroup">
                            <div class="form-group">
                                <label>Webhook URL</label>
                                <input type="url" id="webhook_url" placeholder="https://hooks.slack.com/...">
                            </div>
                        </div>
                    </div>
                    
                    <!-- Severity -->
                    <div class="form-section">
                        <div class="section-title">Severity Level</div>
                        <div class="severity-pills">
                            <div class="severity-pill low" onclick="selectSeverity('low')">Low</div>
                            <div class="severity-pill medium selected" onclick="selectSeverity('medium')">Medium</div>
                            <div class="severity-pill high" onclick="selectSeverity('high')">High</div>
                            <div class="severity-pill critical" onclick="selectSeverity('critical')">Critical</div>
                        </div>
                        <input type="hidden" id="severity" value="medium">
                    </div>
                    
                    <!-- Enable -->
                    <div class="form-section">
                        <div class="toggle-row">
                            <span><strong>Enable Alert</strong></span>
                            <label class="toggle">
                                <input type="checkbox" id="enabled" checked>
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Create Alert</button>
                </form>
            </div>
            
            <!-- Stats Sidebar -->
            <div>
                <div class="card" style="margin-bottom: 24px;">
                    <div class="card-title">📈 Alert Statistics</div>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="value" id="statTotal">0</div>
                            <div class="label">Total Alerts</div>
                        </div>
                        <div class="stat-card">
                            <div class="value" id="statEnabled">0</div>
                            <div class="label">Active</div>
                        </div>
                        <div class="stat-card">
                            <div class="value" id="statTriggered">0</div>
                            <div class="label">Triggered (24h)</div>
                        </div>
                        <div class="stat-card">
                            <div class="value" id="statCritical">0</div>
                            <div class="label">Critical</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">💡 Quick Tips</div>
                    <ul style="font-size: 0.85rem; color: var(--text-muted); padding-left: 20px; line-height: 1.8;">
                        <li><strong>Static:</strong> Best for known thresholds (e.g., &gt;100 emails/day)</li>
                        <li><strong>Smart:</strong> Detects unusual patterns automatically</li>
                        <li><strong>Z-Score 2.5:</strong> ~99% confidence the value is unusual</li>
                        <li><strong>Consecutive:</strong> Reduce false positives by requiring multiple anomalies</li>
                        <li><strong>Cooldown:</strong> Prevent alert storms</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Manage Tab -->
        <div id="manageTab" style="display: none;">
            <div class="card">
                <div class="card-title">📋 All Alerts</div>
                <div class="alert-list" id="alertList">Loading...</div>
            </div>
        </div>
        
        <!-- History Tab -->
        <div id="historyTab" style="display: none;">
            <div class="card">
                <div class="card-title">🔔 Recent Triggers</div>
                <div class="alert-list" id="historyList">Loading...</div>
            </div>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        // State
        let emails = [];
        let keywords = [];
        let currentAlertType = 'static';
        let currentSeverity = 'medium';
        
        // Tab switching
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab:nth-child(${tab === 'create' ? 1 : tab === 'manage' ? 2 : 3})`).classList.add('active');
            
            document.getElementById('createTab').style.display = tab === 'create' ? 'grid' : 'none';
            document.getElementById('manageTab').style.display = tab === 'manage' ? 'block' : 'none';
            document.getElementById('historyTab').style.display = tab === 'history' ? 'block' : 'none';
            
            if (tab === 'manage') loadAlerts();
            if (tab === 'history') loadHistory();
        }
        
        // Alert type selection
        function selectAlertType(type) {
            currentAlertType = type;
            document.getElementById('alert_type').value = type;
            
            document.querySelectorAll('.alert-type-card').forEach(c => c.classList.remove('selected'));
            document.querySelector(`.alert-type-card[data-type="${type}"]`).classList.add('selected');
            
            // Toggle sections
            document.getElementById('thresholdSection').classList.toggle('visible', type === 'static');
            document.getElementById('anomalySection').classList.toggle('visible', type === 'smart');
            document.getElementById('baselineGroup').classList.toggle('visible', type === 'smart');
        }
        
        // Severity selection
        function selectSeverity(severity) {
            currentSeverity = severity;
            document.getElementById('severity').value = severity;
            
            document.querySelectorAll('.severity-pill').forEach(p => p.classList.remove('selected'));
            document.querySelector(`.severity-pill.${severity}`).classList.add('selected');
        }
        
        // Metric options
        function updateMetricOptions() {
            const metricType = document.getElementById('metric_type').value;
            
            document.getElementById('entityTypeGroup').style.display = 
                metricType === 'entity_mentions' ? 'flex' : 'none';
            document.getElementById('entityValueGroup').style.display = 
                metricType === 'entity_mentions' ? 'block' : 'none';
            document.getElementById('keywordsGroup').classList.toggle('visible', 
                metricType === 'keyword_matches');
        }
        
        // Keywords handling
        function addKeyword() {
            const input = document.getElementById('keywordInput');
            const keyword = input.value.trim();
            if (keyword && !keywords.includes(keyword)) {
                keywords.push(keyword);
                renderKeywords();
                input.value = '';
            }
        }
        
        document.getElementById('keywordInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addKeyword();
            }
        });
        
        function removeKeyword(index) {
            keywords.splice(index, 1);
            renderKeywords();
        }
        
        function renderKeywords() {
            document.getElementById('keywordList').innerHTML = keywords.map((kw, i) => `
                <span class="keyword-tag">${kw} <button type="button" onclick="removeKeyword(${i})">&times;</button></span>
            `).join('');
        }
        
        // Email handling
        document.getElementById('emailInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const email = this.value.trim();
                if (email && /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email) && !emails.includes(email)) {
                    emails.push(email);
                    renderEmails();
                    this.value = '';
                }
            }
        });
        
        function removeEmail(index) {
            emails.splice(index, 1);
            renderEmails();
        }
        
        function renderEmails() {
            const container = document.getElementById('emailContainer');
            container.innerHTML = emails.map((email, i) => `
                <span class="email-tag">${email} <button type="button" onclick="removeEmail(${i})">&times;</button></span>
            `).join('') + '<input type="email" class="email-input" id="emailInput" placeholder="Enter email and press Enter">';
            
            document.getElementById('emailInput').addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const email = this.value.trim();
                    if (email && /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email) && !emails.includes(email)) {
                        emails.push(email);
                        renderEmails();
                    }
                }
            });
        }
        
        // Webhook toggle
        document.getElementById('webhook_enabled').addEventListener('change', function() {
            document.getElementById('webhookUrlGroup').classList.toggle('visible', this.checked);
        });
        
        // Algorithm toggle
        document.getElementById('algorithm').addEventListener('change', function() {
            document.getElementById('pctChangeGroup').classList.toggle('visible', this.value === 'percentage_change');
            document.getElementById('zscoreThresholdGroup').style.display = 
                this.value === 'percentage_change' ? 'none' : 'flex';
        });
        
        // Form submission
        document.getElementById('alertForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                name: document.getElementById('name').value,
                description: document.getElementById('description').value || null,
                alert_type: currentAlertType,
                metric: {
                    metric_type: document.getElementById('metric_type').value,
                    entity_type: document.getElementById('entity_type').value,
                    entity_value: document.getElementById('entity_value').value || null,
                    keywords: keywords.length ? keywords : null
                },
                time_window: {
                    window_size: parseInt(document.getElementById('window_size').value),
                    window_unit: document.getElementById('window_unit').value,
                    check_frequency: parseInt(document.getElementById('check_frequency').value),
                    baseline_days: parseInt(document.getElementById('baseline_days').value)
                },
                threshold: currentAlertType === 'static' ? {
                    operator: document.getElementById('operator').value,
                    value: parseFloat(document.getElementById('threshold_value').value)
                } : null,
                anomaly: currentAlertType === 'smart' ? {
                    algorithm: document.getElementById('algorithm').value,
                    zscore_threshold: parseFloat(document.getElementById('zscore_threshold').value),
                    percentage_threshold: parseFloat(document.getElementById('percentage_threshold').value),
                    min_baseline_count: 5
                } : null,
                cooldown: {
                    enabled: document.getElementById('cooldown_enabled').checked,
                    cooldown_minutes: parseInt(document.getElementById('cooldown_minutes').value),
                    max_alerts_per_day: parseInt(document.getElementById('max_alerts_per_day').value),
                    consecutive_anomalies: parseInt(document.getElementById('consecutive_anomalies').value)
                },
                notifications: {
                    email_enabled: document.getElementById('email_enabled').checked,
                    email_recipients: emails,
                    dashboard_enabled: document.getElementById('dashboard_enabled').checked,
                    webhook_enabled: document.getElementById('webhook_enabled').checked,
                    webhook_url: document.getElementById('webhook_url').value || null,
                    include_chart: true
                },
                severity: currentSeverity,
                enabled: document.getElementById('enabled').checked
            };
            
            try {
                const response = await fetch('/api/v1/sprinklr-alerts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                if (response.ok) {
                    showToast('Alert created successfully!', 'success');
                    document.getElementById('alertForm').reset();
                    emails = [];
                    keywords = [];
                    renderEmails();
                    renderKeywords();
                    selectAlertType('static');
                    selectSeverity('medium');
                    loadStats();
                } else {
                    const error = await response.json();
                    showToast(error.detail || 'Failed to create alert', 'error');
                }
            } catch (err) {
                showToast('Network error: ' + err.message, 'error');
            }
        });
        
        // Load alerts
        async function loadAlerts() {
            try {
                const response = await fetch('/api/v1/sprinklr-alerts');
                const data = await response.json();
                
                const container = document.getElementById('alertList');
                if (!data.alerts.length) {
                    container.innerHTML = '<p style="color: var(--text-muted);">No alerts created yet.</p>';
                    return;
                }
                
                container.innerHTML = data.alerts.map(alert => `
                    <div class="alert-item">
                        <div class="alert-item-info">
                            <h4>${alert.name}</h4>
                            <p>${alert.description || 'No description'}</p>
                            <div class="alert-item-meta">
                                <span class="meta-tag">${alert.alert_type}</span>
                                <span class="meta-tag">${alert.metric?.metric_type || 'email_volume'}</span>
                                <span class="meta-tag" style="color: var(--accent-${alert.severity === 'critical' ? 'red' : alert.severity === 'high' ? 'orange' : alert.severity === 'medium' ? 'yellow' : 'green'})">${alert.severity}</span>
                                <span class="meta-tag">${alert.enabled ? '✓ Enabled' : '✗ Disabled'}</span>
                                <span class="meta-tag">Triggered: ${alert.trigger_count}x</span>
                            </div>
                        </div>
                        <div class="alert-item-actions">
                            <button class="btn btn-outline btn-sm" onclick="evaluateAlert('${alert.id}')">Test</button>
                            <button class="btn btn-outline btn-sm btn-danger" onclick="deleteAlert('${alert.id}')">Delete</button>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                document.getElementById('alertList').innerHTML = '<p style="color: var(--accent-red);">Failed to load alerts</p>';
            }
        }
        
        // Load history
        async function loadHistory() {
            try {
                const response = await fetch('/api/v1/sprinklr-alerts/triggered/all');
                const data = await response.json();
                
                const container = document.getElementById('historyList');
                if (!data.triggered.length) {
                    container.innerHTML = '<p style="color: var(--text-muted);">No alerts triggered yet.</p>';
                    return;
                }
                
                container.innerHTML = data.triggered.map(h => `
                    <div class="alert-item">
                        <div class="alert-item-info">
                            <h4>${h.alert_name}</h4>
                            <p>${h.trigger_reason || 'Threshold exceeded'}</p>
                            <div class="alert-item-meta">
                                <span class="meta-tag">Value: ${h.metric_value}</span>
                                <span class="meta-tag">Baseline: ${h.baseline_value}</span>
                                ${h.zscore ? `<span class="meta-tag">Z-Score: ${h.zscore}</span>` : ''}
                                <span class="meta-tag">${new Date(h.triggered_at).toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                document.getElementById('historyList').innerHTML = '<p style="color: var(--accent-red);">Failed to load history</p>';
            }
        }
        
        // Evaluate alert
        async function evaluateAlert(id) {
            try {
                const response = await fetch(`/api/v1/sprinklr-alerts/${id}/evaluate`, { method: 'POST' });
                const result = await response.json();
                
                if (result.triggered) {
                    showToast(`🚨 TRIGGERED: ${result.trigger_reason}`, 'error');
                } else {
                    showToast(`✓ Not triggered. Current: ${result.current_value}, Baseline: ${result.baseline_value}`, 'success');
                }
                loadStats();
            } catch (err) {
                showToast('Failed to evaluate alert', 'error');
            }
        }
        
        // Delete alert
        async function deleteAlert(id) {
            if (!confirm('Delete this alert?')) return;
            
            try {
                const response = await fetch(`/api/v1/sprinklr-alerts/${id}`, { method: 'DELETE' });
                if (response.ok) {
                    showToast('Alert deleted', 'success');
                    loadAlerts();
                    loadStats();
                }
            } catch (err) {
                showToast('Failed to delete', 'error');
            }
        }
        
        // Load stats
        async function loadStats() {
            try {
                const response = await fetch('/api/v1/sprinklr-alerts/stats');
                const stats = await response.json();
                
                document.getElementById('statTotal').textContent = stats.total_alerts;
                document.getElementById('statEnabled').textContent = stats.enabled_alerts;
                document.getElementById('statTriggered').textContent = stats.triggered_last_24h;
                document.getElementById('statCritical').textContent = stats.by_severity?.critical || 0;
            } catch (err) {
                console.error('Failed to load stats');
            }
        }
        
        // Toast
        function showToast(message, type) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type + ' show';
            setTimeout(() => toast.classList.remove('show'), 4000);
        }
        
        // Initialize
        loadStats();
        updateMetricOptions();
    </script>
</body>
</html>
    '''
    return HTMLResponse(content=html_content)


# ============ Form Options ============

@router.get("/options", response_model=SprinklrFormOptionsResponse)
def get_form_options():
    """Get available options for the alert creation form."""
    return SprinklrFormOptionsResponse()


# ============ Statistics ============

@router.get("/stats")
def get_alert_stats(db: Session = Depends(get_db)):
    """Get alert statistics for dashboard."""
    service = SprinklrAlertService(db)
    return service.get_alert_stats()


# ============ CRUD Operations ============

@router.get("", response_model=SprinklrAlertListResponse)
def list_alerts(
    enabled_only: bool = Query(False),
    alert_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List all Sprinklr-style alerts."""
    service = SprinklrAlertService(db)
    alerts, total = service.list(enabled_only=enabled_only, alert_type=alert_type, limit=limit)
    
    return SprinklrAlertListResponse(
        total=total,
        alerts=[SprinklrAlertResponse.model_validate(a) for a in alerts]
    )


@router.post("", response_model=SprinklrAlertResponse)
def create_alert(data: SprinklrAlertCreate, db: Session = Depends(get_db)):
    """
    Create a new Sprinklr-style alert.
    
    ## Alert Types
    
    - **static**: Threshold-based alerts (e.g., > 100 emails/day)
    - **smart**: AI/anomaly-based alerts using Z-score or EWMA
    
    ## Metrics
    
    - **email_volume**: Count of emails
    - **unique_senders**: Count of unique senders
    - **entity_mentions**: Count of entity mentions (filter by type)
    - **keyword_matches**: Count of keyword occurrences
    """
    service = SprinklrAlertService(db)
    
    existing = service.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Alert with this name already exists")
    
    alert = service.create(data)
    return SprinklrAlertResponse.model_validate(alert)


@router.get("/{alert_id}", response_model=SprinklrAlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific alert by ID."""
    service = SprinklrAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return SprinklrAlertResponse.model_validate(alert)


@router.put("/{alert_id}", response_model=SprinklrAlertResponse)
def update_alert(alert_id: str, data: SprinklrAlertUpdate, db: Session = Depends(get_db)):
    """Update an alert."""
    service = SprinklrAlertService(db)
    alert = service.update(alert_id, data)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return SprinklrAlertResponse.model_validate(alert)


@router.delete("/{alert_id}")
def delete_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete an alert."""
    service = SprinklrAlertService(db)
    success = service.delete(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert deleted successfully"}


# ============ Evaluation ============

@router.post("/{alert_id}/evaluate", response_model=EvaluationResult)
def evaluate_alert(alert_id: str, db: Session = Depends(get_db)):
    """
    Manually evaluate an alert.
    
    Returns detailed evaluation result including:
    - Whether the alert would trigger
    - Current metric value vs baseline
    - Z-score (for smart alerts)
    - Time series data for visualization
    - Top contributors
    """
    service = SprinklrAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    result = service.evaluate(alert)
    return EvaluationResult(**result)


@router.post("/evaluate-all")
def evaluate_all_alerts(db: Session = Depends(get_db)):
    """Evaluate all enabled alerts."""
    service = SprinklrAlertService(db)
    triggered = service.evaluate_all()
    
    return {
        "evaluated": True,
        "triggered_count": len(triggered),
        "triggered_alerts": triggered
    }


# ============ History ============

@router.get("/triggered/all")
def get_all_triggered(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all recently triggered alerts."""
    service = SprinklrAlertService(db)
    triggered = service.get_triggered_alerts(limit=limit)
    
    return {
        "total": len(triggered),
        "triggered": triggered
    }


@router.get("/{alert_id}/history")
def get_alert_history(
    alert_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get trigger history for a specific alert."""
    service = SprinklrAlertService(db)
    
    alert = service.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    history, total = service.get_history(alert_id=alert_id, limit=limit)
    
    return {
        "total": total,
        "history": [
            {
                "id": h.id,
                "triggered_at": h.triggered_at.isoformat(),
                "metric_value": h.metric_value,
                "baseline_value": h.baseline_value,
                "zscore": h.zscore,
                "trigger_reason": h.trigger_reason,
                "top_contributors": h.top_contributors
            }
            for h in history
        ]
    }

