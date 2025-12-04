import { useState, useEffect, useCallback } from 'react';
import { unifiedAlertsAPI } from '../api/apiService';
import './SmartAlerts.css';

function SmartAlerts() {
  const [alerts, setAlerts] = useState({ dataQuality: [], entityType: [], smartAI: [] });
  const [stats, setStats] = useState(null);
  const [options, setOptions] = useState(null);
  const [entityValues, setEntityValues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [evaluating, setEvaluating] = useState(null);
  const [activeAlertType, setActiveAlertType] = useState('all');

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    alertCategory: 'entity_type', // data_quality, entity_type, smart_ai
    severity: 'medium',
    enabled: true,
    // Data Quality specific
    quality_type: 'format_error',
    file_format: 'all',
    file_size_min: null,
    file_size_max: null,
    // Entity Type specific
    entity_type: 'ALL',
    entity_value: '',
    detection_algorithm: 'dbscan',
    dbscan_eps: 0.5,
    dbscan_min_samples: 3,
    kmeans_clusters: 3,
    sensitivity: 1.5,
    window_hours: 24,
    baseline_days: 7,
    // Smart AI specific
    use_semantic_search: true,
    similarity_threshold: 0.7,
  });

  const fetchAllAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [dq, et, sa] = await Promise.all([
        unifiedAlertsAPI.dataQuality.list(),
        unifiedAlertsAPI.entityType.list(),
        unifiedAlertsAPI.smartAI.list(),
      ]);
      
      setAlerts({
        dataQuality: dq.alerts || [],
        entityType: et.alerts || [],
        smartAI: sa.alerts || [],
      });
    } catch (err) {
      console.error('Fetch alerts error:', err);
      setError(err.response?.data?.detail || 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await unifiedAlertsAPI.getStats();
      setStats(response);
    } catch (err) {
      console.error('Fetch stats error:', err);
    }
  }, []);

  const fetchOptions = useCallback(async () => {
    try {
      const response = await unifiedAlertsAPI.getOptions();
      setOptions(response);
    } catch (err) {
      console.error('Fetch options error:', err);
    }
  }, []);

  const fetchEntityValues = useCallback(async (entityType = null) => {
    try {
      const response = await unifiedAlertsAPI.getEntityValues(entityType, 200);
      setEntityValues(response.entity_values || []);
    } catch (err) {
      console.error('Fetch entity values error:', err);
    }
  }, []);

  useEffect(() => {
    fetchAllAlerts();
    fetchStats();
    fetchOptions();
    fetchEntityValues();
  }, [fetchAllAlerts, fetchStats, fetchOptions, fetchEntityValues]);

  const handleCreateAlert = async (e) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    try {
      let alertData;
      
      if (formData.alertCategory === 'data_quality') {
        alertData = {
          name: formData.name,
          description: formData.description || null,
          quality_type: formData.quality_type,
          file_format: formData.file_format,
          file_size_min: formData.file_size_min || null,
          file_size_max: formData.file_size_max || null,
          severity: formData.severity,
          enabled: formData.enabled,
        };
        await unifiedAlertsAPI.dataQuality.create(alertData);
      } else if (formData.alertCategory === 'entity_type') {
        alertData = {
          name: formData.name,
          description: formData.description || null,
          entity_type: formData.entity_type,
          entity_value: formData.entity_value || null,
          detection_algorithm: formData.detection_algorithm,
          dbscan_eps: formData.dbscan_eps,
          dbscan_min_samples: formData.dbscan_min_samples,
          kmeans_clusters: formData.kmeans_clusters,
          sensitivity: formData.sensitivity,
          window_hours: formData.window_hours,
          baseline_days: formData.baseline_days,
          severity: formData.severity,
          enabled: formData.enabled,
        };
        await unifiedAlertsAPI.entityType.create(alertData);
      } else if (formData.alertCategory === 'smart_ai') {
        alertData = {
          name: formData.name,
          description: formData.description,
          detection_algorithm: formData.detection_algorithm,
          use_semantic_search: formData.use_semantic_search,
          similarity_threshold: formData.similarity_threshold,
          severity: formData.severity,
          enabled: formData.enabled,
        };
        await unifiedAlertsAPI.smartAI.create(alertData);
      }

      setShowCreateModal(false);
      resetForm();
      fetchAllAlerts();
      fetchStats();
    } catch (err) {
      console.error('Create alert error:', err);
      setCreateError(err.response?.data?.detail || 'Failed to create alert');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteAlert = async (alertId, category) => {
    if (!window.confirm('Are you sure you want to delete this alert?')) return;

    try {
      if (category === 'data_quality') {
        await unifiedAlertsAPI.dataQuality.delete(alertId);
      } else if (category === 'entity_type') {
        await unifiedAlertsAPI.entityType.delete(alertId);
      } else if (category === 'smart_ai') {
        await unifiedAlertsAPI.smartAI.delete(alertId);
      }
      fetchAllAlerts();
      fetchStats();
    } catch (err) {
      console.error('Delete alert error:', err);
      alert('Failed to delete alert');
    }
  };

  const handleToggleAlert = async (alertId, category) => {
    try {
      if (category === 'data_quality') {
        await unifiedAlertsAPI.dataQuality.toggle(alertId);
      } else if (category === 'entity_type') {
        await unifiedAlertsAPI.entityType.toggle(alertId);
      } else if (category === 'smart_ai') {
        await unifiedAlertsAPI.smartAI.toggle(alertId);
      }
      fetchAllAlerts();
      fetchStats();
    } catch (err) {
      console.error('Toggle alert error:', err);
    }
  };

  const handleEvaluateAlert = async (alertId, category) => {
    setEvaluating(`${category}-${alertId}`);
    try {
      let result;
      if (category === 'data_quality') {
        result = await unifiedAlertsAPI.dataQuality.evaluate(alertId);
        alert(`Data Quality Alert Evaluation:\n\nTriggered: ${result.triggered ? 'Yes ✓' : 'No'}\nIssues Found: ${result.issues_found}\n${result.issues?.length ? result.issues.map(i => `• ${i.error_type}: ${i.error_details}`).join('\n') : ''}`);
      } else if (category === 'entity_type') {
        result = await unifiedAlertsAPI.entityType.evaluate(alertId);
        alert(`Entity Type Alert Evaluation:\n\nAnomaly Detected: ${result.is_anomaly ? 'Yes ✓' : 'No'}\nAnomaly Type: ${result.anomaly_type || 'N/A'}\nCurrent Value: ${result.current_value?.toFixed(2)}\nBaseline Value: ${result.baseline_value?.toFixed(2)}\nAlgorithm: ${result.algorithm}\n${result.trigger_reason || ''}`);
      } else if (category === 'smart_ai') {
        result = await unifiedAlertsAPI.smartAI.evaluate(alertId);
        alert(`Smart AI Alert Evaluation:\n\nTriggered: ${result.triggered ? 'Yes ✓' : 'No'}\nMatched Emails: ${result.matched_emails?.length || 0}\nEntity Anomaly: ${result.entity_anomaly ? 'Yes' : 'No'}\n${result.trigger_reason || ''}`);
      }
      fetchAllAlerts();
      fetchStats();
    } catch (err) {
      console.error('Evaluate alert error:', err);
      alert('Failed to evaluate alert');
    } finally {
      setEvaluating(null);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      alertCategory: 'entity_type',
      severity: 'medium',
      enabled: true,
      quality_type: 'format_error',
      file_format: 'all',
      file_size_min: null,
      file_size_max: null,
      entity_type: 'ALL',
      entity_value: '',
      detection_algorithm: 'dbscan',
      dbscan_eps: 0.5,
      dbscan_min_samples: 3,
      kmeans_clusters: 3,
      sensitivity: 1.5,
      window_hours: 24,
      baseline_days: 7,
      use_semantic_search: true,
      similarity_threshold: 0.7,
    });
    setCreateError(null);
  };

  const getSeverityColor = (severity) => {
    const colors = {
      low: '#22c55e',
      medium: '#eab308',
      high: '#f97316',
      critical: '#ef4444',
    };
    return colors[severity] || '#6b7280';
  };

  const getCategoryIcon = (category) => {
    const icons = {
      data_quality: '📊',
      entity_type: '🏷️',
      smart_ai: '🤖',
    };
    return icons[category] || '🔔';
  };

  const getCategoryLabel = (category) => {
    const labels = {
      data_quality: 'Data Quality',
      entity_type: 'Entity Type',
      smart_ai: 'Smart AI',
    };
    return labels[category] || category;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getAllAlerts = () => {
    const all = [];
    alerts.dataQuality.forEach(a => all.push({ ...a, category: 'data_quality' }));
    alerts.entityType.forEach(a => all.push({ ...a, category: 'entity_type' }));
    alerts.smartAI.forEach(a => all.push({ ...a, category: 'smart_ai' }));
    return all.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  };

  const getFilteredAlerts = () => {
    if (activeAlertType === 'all') return getAllAlerts();
    if (activeAlertType === 'data_quality') return alerts.dataQuality.map(a => ({ ...a, category: 'data_quality' }));
    if (activeAlertType === 'entity_type') return alerts.entityType.map(a => ({ ...a, category: 'entity_type' }));
    if (activeAlertType === 'smart_ai') return alerts.smartAI.map(a => ({ ...a, category: 'smart_ai' }));
    return [];
  };

  return (
    <div className="alerts-container">
      <div className="alerts-header">
        <div className="header-content">
          <h1>Unified Alerts</h1>
          <p className="alerts-description">
            Create and manage Data Quality, Entity Type, and Smart AI alerts with DBSCAN/K-Means anomaly detection.
          </p>
        </div>
        <button className="create-btn" onClick={() => setShowCreateModal(true)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Create Alert
        </button>
      </div>

      {/* Stats Summary */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value">{stats?.total_alerts || 0}</div>
          <div className="stat-label">Total Alerts</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.enabled_alerts || 0}</div>
          <div className="stat-label">Active</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.triggered_last_24h || 0}</div>
          <div className="stat-label">Triggered (24h)</div>
        </div>
        <div className="stat-card critical">
          <div className="stat-value">{stats?.anomalies_detected || 0}</div>
          <div className="stat-label">Anomalies</div>
        </div>
      </div>

      {/* Alert Type Filter Tabs */}
      <div className="alert-type-tabs">
        <button 
          className={`tab-btn ${activeAlertType === 'all' ? 'active' : ''}`}
          onClick={() => setActiveAlertType('all')}
        >
          All ({getAllAlerts().length})
        </button>
        <button 
          className={`tab-btn ${activeAlertType === 'data_quality' ? 'active' : ''}`}
          onClick={() => setActiveAlertType('data_quality')}
        >
          📊 Data Quality ({alerts.dataQuality.length})
        </button>
        <button 
          className={`tab-btn ${activeAlertType === 'entity_type' ? 'active' : ''}`}
          onClick={() => setActiveAlertType('entity_type')}
        >
          🏷️ Entity Type ({alerts.entityType.length})
        </button>
        <button 
          className={`tab-btn ${activeAlertType === 'smart_ai' ? 'active' : ''}`}
          onClick={() => setActiveAlertType('smart_ai')}
        >
          🤖 Smart AI ({alerts.smartAI.length})
        </button>
      </div>

      {/* Alerts List Section */}
      <div className="alerts-list-section">
        <div className="section-header">
          <h2>Configured Alerts</h2>
          <button className="refresh-btn" onClick={fetchAllAlerts}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
              <path d="M21 21v-5h-5" />
            </svg>
          </button>
        </div>

        {loading && (
          <div className="loading-state">
            <div className="loader"></div>
            <p>Loading alerts...</p>
          </div>
        )}

        {error && (
          <div className="error-state">
            <p>{error}</p>
            <button onClick={fetchAllAlerts}>Retry</button>
          </div>
        )}

        {!loading && !error && getFilteredAlerts().length === 0 && (
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <p>No alerts configured yet</p>
            <span>Create your first alert to start monitoring</span>
          </div>
        )}

        {!loading && !error && getFilteredAlerts().length > 0 && (
          <div className="alerts-grid">
            {getFilteredAlerts().map((alert) => (
              <div key={`${alert.category}-${alert.id}`} className={`alert-card ${!alert.enabled ? 'disabled' : ''}`}>
                <div className="alert-card-header">
                  <div className="alert-icon">
                    {getCategoryIcon(alert.category)}
                  </div>
                  <div className="alert-info">
                    <h3>{alert.name}</h3>
                    <span className="alert-type">
                      {getCategoryLabel(alert.category)}
                      {alert.entity_type && ` • ${alert.entity_type}`}
                      {alert.quality_type && ` • ${alert.quality_type.replace('_', ' ')}`}
                    </span>
                  </div>
                  <div 
                    className="severity-badge"
                    style={{ backgroundColor: getSeverityColor(alert.severity) }}
                  >
                    {alert.severity}
                  </div>
                </div>

                {alert.description && (
                  <p className="alert-description">{alert.description}</p>
                )}

                {/* Alert Configuration Summary */}
                <div className="alert-config">
                  {alert.detection_algorithm && (
                    <span className="config-item algorithm">
                      {alert.detection_algorithm.toUpperCase()}
                    </span>
                  )}
                  {alert.file_format && alert.file_format !== 'all' && (
                    <span className="config-item">
                      {alert.file_format.toUpperCase()}
                    </span>
                  )}
                  {alert.window_hours && (
                    <span className="config-item">
                      {alert.window_hours}h window
                    </span>
                  )}
                  {alert.entity_value && (
                    <span className="config-item entity-value">
                      "{alert.entity_value}"
                    </span>
                  )}
                </div>

                <div className="alert-meta">
                  <span className="meta-item">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="4" width="18" height="18" rx="2" />
                      <line x1="16" y1="2" x2="16" y2="6" />
                      <line x1="8" y1="2" x2="8" y2="6" />
                      <line x1="3" y1="10" x2="21" y2="10" />
                    </svg>
                    Last triggered: {formatDate(alert.last_triggered_at)}
                  </span>
                  <span className="meta-item">
                    🔔 {alert.trigger_count || 0} times
                  </span>
                </div>

                <div className="alert-actions">
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={alert.enabled}
                      onChange={() => handleToggleAlert(alert.id, alert.category)}
                    />
                    <span className="toggle-slider"></span>
                    <span className="toggle-label">{alert.enabled ? 'Active' : 'Inactive'}</span>
                  </label>
                  
                  <div className="action-buttons">
                    <button 
                      className="evaluate-btn"
                      onClick={() => handleEvaluateAlert(alert.id, alert.category)}
                      disabled={evaluating === `${alert.category}-${alert.id}`}
                      title="Evaluate Alert"
                    >
                      {evaluating === `${alert.category}-${alert.id}` ? (
                        <span className="mini-loader"></span>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polygon points="5 3 19 12 5 21 5 3" />
                        </svg>
                      )}
                    </button>
                    <button 
                      className="delete-btn"
                      onClick={() => handleDeleteAlert(alert.id, alert.category)}
                      title="Delete Alert"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                        <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Alert Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create Alert</h2>
              <button className="close-btn" onClick={() => setShowCreateModal(false)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreateAlert} className="modal-form">
              {createError && (
                <div className="form-error">{createError}</div>
              )}

              {/* Alert Type Selection */}
              <div className="form-section">
                <h3 className="section-title">Alert Type</h3>
                <div className="alert-type-selector">
                  <button
                    type="button"
                    className={`type-btn ${formData.alertCategory === 'data_quality' ? 'active' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, alertCategory: 'data_quality' }))}
                  >
                    <span className="type-icon">📊</span>
                    <span className="type-label">Data Quality</span>
                    <span className="type-desc">Monitor file imports and data issues</span>
                  </button>
                  <button
                    type="button"
                    className={`type-btn ${formData.alertCategory === 'entity_type' ? 'active' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, alertCategory: 'entity_type' }))}
                  >
                    <span className="type-icon">🏷️</span>
                    <span className="type-label">Entity Type</span>
                    <span className="type-desc">Detect anomalies in entity mentions</span>
                  </button>
                  <button
                    type="button"
                    className={`type-btn ${formData.alertCategory === 'smart_ai' ? 'active' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, alertCategory: 'smart_ai' }))}
                  >
                    <span className="type-icon">🤖</span>
                    <span className="type-label">Smart AI</span>
                    <span className="type-desc">Natural language description to alert</span>
                  </button>
                </div>
              </div>

              {/* Basic Info */}
              <div className="form-section">
                <h3 className="section-title">Alert Details</h3>
                
                <div className="form-group">
                  <label>Alert Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., High Volume Alert"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Description {formData.alertCategory === 'smart_ai' ? '*' : ''}</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder={formData.alertCategory === 'smart_ai' 
                      ? "Describe what you want to monitor in natural language. E.g., 'Alert me when there's unusual activity mentioning specific people or organizations'"
                      : "What does this alert monitor?"}
                    rows={formData.alertCategory === 'smart_ai' ? 4 : 2}
                    required={formData.alertCategory === 'smart_ai'}
                  />
                  {formData.alertCategory === 'smart_ai' && (
                    <span className="form-hint">
                      💡 The system will automatically extract entities, keywords, and patterns from your description
                    </span>
                  )}
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Severity *</label>
                    <select
                      value={formData.severity}
                      onChange={(e) => setFormData(prev => ({ ...prev, severity: e.target.value }))}
                    >
                      {(options?.severities || [
                        { value: 'low', label: 'Low' },
                        { value: 'medium', label: 'Medium' },
                        { value: 'high', label: 'High' },
                        { value: 'critical', label: 'Critical' },
                      ]).map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Data Quality Specific Fields */}
              {formData.alertCategory === 'data_quality' && (
                <div className="form-section">
                  <h3 className="section-title">Data Quality Configuration</h3>
                  
                  <div className="form-row">
                    <div className="form-group">
                      <label>Quality Issue Type *</label>
                      <select
                        value={formData.quality_type}
                        onChange={(e) => setFormData(prev => ({ ...prev, quality_type: e.target.value }))}
                      >
                        {(options?.quality_types || [
                          { value: 'format_error', label: 'Format Error' },
                          { value: 'missing_fields', label: 'Missing Required Fields' },
                          { value: 'encoding_issue', label: 'Encoding Issue' },
                          { value: 'size_limit', label: 'File Size Limit Exceeded' },
                          { value: 'corruption', label: 'Data Corruption' },
                          { value: 'duplicate_data', label: 'Duplicate Data' },
                        ]).map(t => (
                          <option key={t.value} value={t.value}>{t.label}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label>File Format</label>
                      <select
                        value={formData.file_format}
                        onChange={(e) => setFormData(prev => ({ ...prev, file_format: e.target.value }))}
                      >
                        {(options?.file_formats || [
                          { value: 'all', label: 'All Formats' },
                          { value: 'csv', label: 'CSV Files' },
                          { value: 'eml', label: 'Email Files (.eml)' },
                          { value: 'pst', label: 'Outlook Files (.pst)' },
                          { value: 'json', label: 'JSON Files' },
                          { value: 'xml', label: 'XML Files' },
                        ]).map(f => (
                          <option key={f.value} value={f.value}>{f.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {formData.quality_type === 'size_limit' && (
                    <div className="form-row">
                      <div className="form-group">
                        <label>Min File Size (bytes)</label>
                        <input
                          type="number"
                          value={formData.file_size_min || ''}
                          onChange={(e) => setFormData(prev => ({ ...prev, file_size_min: parseInt(e.target.value) || null }))}
                          placeholder="0"
                        />
                      </div>
                      <div className="form-group">
                        <label>Max File Size (bytes)</label>
                        <input
                          type="number"
                          value={formData.file_size_max || ''}
                          onChange={(e) => setFormData(prev => ({ ...prev, file_size_max: parseInt(e.target.value) || null }))}
                          placeholder="e.g., 104857600 (100MB)"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Entity Type Specific Fields */}
              {formData.alertCategory === 'entity_type' && (
                <>
                  <div className="form-section">
                    <h3 className="section-title">Entity Configuration</h3>
                    
                    <div className="form-row">
                      <div className="form-group">
                        <label>Entity Type</label>
                        <select
                          value={formData.entity_type}
                          onChange={(e) => {
                            setFormData(prev => ({ ...prev, entity_type: e.target.value, entity_value: '' }));
                            fetchEntityValues(e.target.value === 'ALL' ? null : e.target.value);
                          }}
                        >
                          {(options?.entity_types || [
                            { value: 'ALL', label: 'All Entities' },
                            { value: 'PERSON', label: 'Person' },
                            { value: 'ORG', label: 'Organization' },
                            { value: 'GPE', label: 'Location (GPE)' },
                            { value: 'MONEY', label: 'Money' },
                            { value: 'DATE', label: 'Date' },
                            { value: 'PRODUCT', label: 'Product' },
                            { value: 'EVENT', label: 'Event' },
                          ]).map(e => (
                            <option key={e.value} value={e.value}>{e.label}</option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group">
                        <label>Specific Entity (optional)</label>
                        <select
                          value={formData.entity_value}
                          onChange={(e) => setFormData(prev => ({ ...prev, entity_value: e.target.value }))}
                        >
                          <option value="">All entities of selected type</option>
                          {entityValues
                            .filter(ev => formData.entity_type === 'ALL' || ev.type === formData.entity_type)
                            .map((ev, idx) => (
                              <option key={idx} value={ev.value}>
                                {ev.value} ({ev.type}) - {ev.count} mentions
                              </option>
                            ))}
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="form-section">
                    <h3 className="section-title">Anomaly Detection (DBSCAN / K-Means)</h3>
                    
                    <div className="form-row">
                      <div className="form-group">
                        <label>Detection Algorithm</label>
                        <select
                          value={formData.detection_algorithm}
                          onChange={(e) => setFormData(prev => ({ ...prev, detection_algorithm: e.target.value }))}
                        >
                          <option value="dbscan">DBSCAN (Density-Based)</option>
                          <option value="kmeans">K-Means Clustering</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label>Sensitivity</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0.5"
                          max="5"
                          value={formData.sensitivity}
                          onChange={(e) => setFormData(prev => ({ ...prev, sensitivity: parseFloat(e.target.value) }))}
                        />
                        <span className="form-hint">Higher = more sensitive (0.5 - 5.0)</span>
                      </div>
                    </div>

                    {formData.detection_algorithm === 'dbscan' && (
                      <div className="form-row">
                        <div className="form-group">
                          <label>DBSCAN Epsilon (eps)</label>
                          <input
                            type="number"
                            step="0.1"
                            min="0.1"
                            max="5"
                            value={formData.dbscan_eps}
                            onChange={(e) => setFormData(prev => ({ ...prev, dbscan_eps: parseFloat(e.target.value) }))}
                          />
                          <span className="form-hint">Distance threshold for clustering</span>
                        </div>
                        <div className="form-group">
                          <label>Min Samples</label>
                          <input
                            type="number"
                            min="1"
                            max="20"
                            value={formData.dbscan_min_samples}
                            onChange={(e) => setFormData(prev => ({ ...prev, dbscan_min_samples: parseInt(e.target.value) }))}
                          />
                          <span className="form-hint">Minimum points to form cluster</span>
                        </div>
                      </div>
                    )}

                    {formData.detection_algorithm === 'kmeans' && (
                      <div className="form-row">
                        <div className="form-group">
                          <label>Number of Clusters (K)</label>
                          <input
                            type="number"
                            min="2"
                            max="10"
                            value={formData.kmeans_clusters}
                            onChange={(e) => setFormData(prev => ({ ...prev, kmeans_clusters: parseInt(e.target.value) }))}
                          />
                          <span className="form-hint">Points far from cluster centers are anomalies</span>
                        </div>
                      </div>
                    )}

                    <div className="form-row">
                      <div className="form-group">
                        <label>Window (hours)</label>
                        <select
                          value={formData.window_hours}
                          onChange={(e) => setFormData(prev => ({ ...prev, window_hours: parseInt(e.target.value) }))}
                        >
                          <option value={1}>1 Hour</option>
                          <option value={6}>6 Hours</option>
                          <option value={12}>12 Hours</option>
                          <option value={24}>24 Hours</option>
                          <option value={48}>48 Hours</option>
                          <option value={168}>1 Week</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Baseline (days)</label>
                        <input
                          type="number"
                          min="1"
                          max="30"
                          value={formData.baseline_days}
                          onChange={(e) => setFormData(prev => ({ ...prev, baseline_days: parseInt(e.target.value) }))}
                        />
                        <span className="form-hint">Days of history for baseline</span>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* Smart AI Specific Fields */}
              {formData.alertCategory === 'smart_ai' && (
                <div className="form-section">
                  <h3 className="section-title">Smart AI Configuration</h3>
                  
                  <div className="form-row">
                    <div className="form-group">
                      <label>Detection Algorithm</label>
                      <select
                        value={formData.detection_algorithm}
                        onChange={(e) => setFormData(prev => ({ ...prev, detection_algorithm: e.target.value }))}
                      >
                        <option value="dbscan">DBSCAN (Density-Based)</option>
                        <option value="kmeans">K-Means Clustering</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Similarity Threshold</label>
                      <input
                        type="number"
                        step="0.05"
                        min="0.3"
                        max="1.0"
                        value={formData.similarity_threshold}
                        onChange={(e) => setFormData(prev => ({ ...prev, similarity_threshold: parseFloat(e.target.value) }))}
                      />
                      <span className="form-hint">Semantic matching threshold (0.3 - 1.0)</span>
                    </div>
                  </div>

                </div>
              )}

              <div className="modal-actions">
                <button type="button" className="cancel-btn" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="submit-btn" disabled={creating}>
                  {creating ? 'Creating...' : 'Create Alert'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default SmartAlerts;
