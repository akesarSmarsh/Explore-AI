import { useState, useEffect, useCallback } from 'react';
import { unifiedAlertsAPI, emailAPI } from '../api/apiService';
import './AlertsDashboard.css';

// Entity colors for display
const ENTITY_COLORS = {
  PERSON: '#f472b6',
  ORG: '#60a5fa',
  GPE: '#34d399',
  MONEY: '#fbbf24',
  DATE: '#a78bfa',
  CARDINAL: '#fb923c',
  PERCENT: '#2dd4bf',
  LOC: '#4ade80',
  PRODUCT: '#f87171',
  EVENT: '#c084fc',
};

function AlertsDashboard() {
  // All alerts list
  const [allAlerts, setAllAlerts] = useState({ dataQuality: [], entityType: [], smartAI: [] });
  const [alertsLoading, setAlertsLoading] = useState(true);
  
  // Selected alert and its graph data
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState(null);
  
  // Recent triggered alerts
  const [recentAlerts, setRecentAlerts] = useState([]);
  
  // Email modal
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [selectedDataPoint, setSelectedDataPoint] = useState(null);
  const [emails, setEmails] = useState([]);
  const [emailsLoading, setEmailsLoading] = useState(false);
  
  // Full email detail view
  const [selectedEmailDetail, setSelectedEmailDetail] = useState(null);
  const [emailDetailLoading, setEmailDetailLoading] = useState(false);
  
  // Hover state for anomaly popup
  const [hoveredPoint, setHoveredPoint] = useState(null);
  
  // Alert rating state
  const [alertRating, setAlertRating] = useState(null);
  const [showRatingPopup, setShowRatingPopup] = useState(false);
  
  // Helper to get entity color
  const getEntityColor = (type) => ENTITY_COLORS[type] || '#6b7280';

  // Fetch all alerts
  const fetchAllAlerts = useCallback(async () => {
    setAlertsLoading(true);
    try {
      const [dq, et, sa] = await Promise.all([
        unifiedAlertsAPI.dataQuality.list(),
        unifiedAlertsAPI.entityType.list(),
        unifiedAlertsAPI.smartAI.list(),
      ]);
      
      setAllAlerts({
        dataQuality: dq.alerts || [],
        entityType: et.alerts || [],
        smartAI: sa.alerts || [],
      });
    } catch (err) {
      console.error('Fetch all alerts error:', err);
    } finally {
      setAlertsLoading(false);
    }
  }, []);

  // Fetch recent triggered alerts
  const fetchRecentAlerts = useCallback(async () => {
    try {
      const response = await unifiedAlertsAPI.dashboard.getRecentAlerts(10);
      setRecentAlerts(response.alerts || []);
    } catch (err) {
      console.error('Fetch recent alerts error:', err);
    }
  }, []);

  useEffect(() => {
    fetchAllAlerts();
    fetchRecentAlerts();
  }, [fetchAllAlerts, fetchRecentAlerts]);

  // Handle alert click - fetch graph data based on alert configuration
  const handleAlertClick = async (alert, category) => {
    setSelectedAlert({ ...alert, category });
    setGraphLoading(true);
    setGraphError(null);
    setGraphData(null);
    
    try {
      // Build params based on alert configuration
      const params = {
        algorithm: alert.detection_algorithm || 'dbscan',
        dbscan_eps: alert.dbscan_eps || 0.5,
        dbscan_min_samples: alert.dbscan_min_samples || 3,
        kmeans_clusters: alert.kmeans_clusters || 3,
        use_all_data: true, // Use all available data for old emails
      };
      
      // Add entity filter for entity type alerts
      if (category === 'entity_type') {
        params.entity_type = alert.entity_type;
        if (alert.entity_value) {
          params.entity_value = alert.entity_value;
        }
      }
      
      // Add semantic search for Smart AI alerts
      if (category === 'smart_ai' && alert.description) {
        params.search_query = alert.description;
        params.similarity_threshold = alert.similarity_threshold || 0.3;
        console.log('Smart AI alert - using semantic search:', alert.description);
      }
      
      const response = await unifiedAlertsAPI.dashboard.getActivity(params);
      setGraphData(response);
    } catch (err) {
      console.error('Fetch graph data error:', err);
      setGraphError(err.response?.data?.detail || 'Failed to load graph data');
    } finally {
      setGraphLoading(false);
    }
  };

  // Handle data point click - fetch emails
  const handleDataPointClick = async (dataPoint) => {
    setSelectedDataPoint(dataPoint);
    setShowEmailModal(true);
    setEmailsLoading(true);
    
    try {
      // Pass the aggregation type from the graph data response
      const aggregationType = graphData?.aggregation || 'hourly';
      
      // Get entity filters from selected alert (for entity type alerts)
      const entityType = selectedAlert?.entity_type || null;
      const entityValue = selectedAlert?.entity_value || null;
      
      // Get semantic search query from selected alert (for Smart AI alerts)
      // Use the description field for semantic search
      const searchQuery = selectedAlert?.category === 'smart_ai' ? selectedAlert?.description : null;
      // Lower threshold for better results (0.3 is more permissive)
      const similarityThreshold = selectedAlert?.similarity_threshold || 0.3;
      
      console.log('Fetching emails for data point:', {
        timestamp: dataPoint.timestamp,
        aggregation: aggregationType,
        category: selectedAlert?.category,
        searchQuery,
        similarityThreshold
      });
      
      const response = await unifiedAlertsAPI.dashboard.getDataPointEmails(
        dataPoint.timestamp, 
        aggregationType, 
        50,
        entityType,
        entityValue,
        searchQuery,
        similarityThreshold
      );
      console.log('Data point emails response:', response);
      setEmails(response.emails || []);
    } catch (err) {
      console.error('Fetch emails error:', err);
      setEmails([]);
    } finally {
      setEmailsLoading(false);
    }
  };

  const closeEmailModal = () => {
    setShowEmailModal(false);
    setSelectedDataPoint(null);
    setEmails([]);
    setSelectedEmailDetail(null);
  };

  // Handle viewing full email details
  const handleViewFullEmail = async (emailId) => {
    setEmailDetailLoading(true);
    try {
      const emailData = await emailAPI.get(emailId);
      setSelectedEmailDetail(emailData);
    } catch (err) {
      console.error('Fetch email detail error:', err);
      alert('Failed to load email details');
    } finally {
      setEmailDetailLoading(false);
    }
  };

  // Close full email detail view (go back to list)
  const closeEmailDetail = () => {
    setSelectedEmailDetail(null);
  };

  // Format full date for email detail
  const formatFullDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Get all alerts as flat list
  const getAllAlertsList = () => {
    const all = [];
    allAlerts.smartAI.forEach(a => all.push({ ...a, category: 'smart_ai', icon: '🤖', typeLabel: 'Smart AI' }));
    allAlerts.entityType.forEach(a => all.push({ ...a, category: 'entity_type', icon: '🏷️', typeLabel: 'Entity Type' }));
    allAlerts.dataQuality.forEach(a => all.push({ ...a, category: 'data_quality', icon: '📊', typeLabel: 'Data Quality' }));
    return all;
  };

  // Format helpers
  const formatDateTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const getAnomalyLabel = (type) => {
    const labels = {
      spike: 'Unusual Volume Spike',
      silence: 'Sudden Silence from Key Entity',
      unusual_pattern: 'Unusual Sentiment Change',
      data_gap: 'Data Gap Detected',
    };
    return labels[type] || 'Anomaly Detected';
  };

  const getSeverityColor = (severity) => {
    const colors = {
      low: '#22c55e',
      medium: '#f59e0b',
      high: '#f97316',
      critical: '#ef4444',
    };
    return colors[severity] || '#6b7280';
  };

  // Chart dimensions
  const chartWidth = 900;
  const chartHeight = 280;
  const padding = { top: 50, right: 40, bottom: 50, left: 70 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;

  // Generate chart elements
  const generateChartElements = () => {
    if (!graphData?.data?.length) return null;
    
    const data = graphData.data;
    const maxCount = Math.max(...data.map(d => d.email_count), 1);
    const baseline = graphData.baseline || 0;
    
    // Generate points
    const points = data.map((d, i) => {
      const x = padding.left + (i / Math.max(data.length - 1, 1)) * plotWidth;
      const y = padding.top + plotHeight - (d.email_count / maxCount) * plotHeight;
      return { x, y, data: d, index: i };
    });
    
    // Create smooth line path
    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    
    // Baseline Y
    const baselineY = padding.top + plotHeight - (baseline / maxCount) * plotHeight;
    
    // Find where normal pattern ends (first anomaly or 70% through)
    const firstAnomalyIndex = data.findIndex(d => d.is_anomaly);
    const normalEndIndex = firstAnomalyIndex > 0 ? firstAnomalyIndex : Math.floor(data.length * 0.7);
    const normalEndX = points[normalEndIndex]?.x || (padding.left + plotWidth * 0.7);
    
    // Y-axis labels
    const yLabels = [0, maxCount * 0.5, maxCount].map(v => ({
      value: Math.round(v),
      y: padding.top + plotHeight - (v / maxCount) * plotHeight
    }));
    
    // X-axis labels (show ~8 labels)
    const step = Math.max(1, Math.floor(data.length / 8));
    const xLabels = data.filter((_, i) => i % step === 0).map((d, i) => ({
      label: formatTime(d.timestamp),
      x: padding.left + ((i * step) / Math.max(data.length - 1, 1)) * plotWidth
    }));
    
    return {
      points,
      pathD,
      baselineY,
      normalEndX,
      yLabels,
      xLabels,
      maxCount
    };
  };

  const chartElements = selectedAlert && graphData ? generateChartElements() : null;

  return (
    <div className="anomaly-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <h1>Anomaly Detection</h1>
        <div className="header-actions">
          <button className="icon-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4M12 8h.01" />
            </svg>
          </button>
          <button className="icon-btn notification">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span className="notification-badge">{recentAlerts.length}</span>
          </button>
          <div className="user-avatar"></div>
        </div>
      </div>

      <div className="dashboard-content">
        {/* Alerts List Sidebar */}
        <div className="alerts-sidebar">
          <div className="sidebar-header">
            <h2>Configured Alerts</h2>
            <span className="count-badge">{getAllAlertsList().length}</span>
          </div>
          
          {alertsLoading ? (
            <div className="sidebar-loading">
              <div className="loader-small"></div>
              <span>Loading alerts...</span>
            </div>
          ) : getAllAlertsList().length === 0 ? (
            <div className="sidebar-empty">
              <p>No alerts configured</p>
              <span>Create alerts in the Alerts tab</span>
            </div>
          ) : (
            <div className="alerts-list">
              {getAllAlertsList().map((alert) => (
                <div
                  key={`${alert.category}-${alert.id}`}
                  className={`alert-list-item ${selectedAlert?.id === alert.id ? 'selected' : ''} ${!alert.enabled ? 'disabled' : ''}`}
                  onClick={() => handleAlertClick(alert, alert.category)}
                >
                  <div className="alert-icon">{alert.icon}</div>
                  <div className="alert-content">
                    <span className="alert-name">{alert.name}</span>
                    <span className="alert-type">{alert.typeLabel}</span>
                  </div>
                  <div 
                    className="alert-severity"
                    style={{ backgroundColor: getSeverityColor(alert.severity) }}
                  ></div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Main Graph Area */}
        <div className="graph-area">
          {!selectedAlert ? (
            <div className="graph-placeholder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M3 3v18h18" />
                <path d="m19 9-5 5-4-4-3 3" />
              </svg>
              <h3>Select an Alert</h3>
              <p>Click on an alert from the sidebar to view its communication activity graph</p>
            </div>
          ) : (
            <>
              {/* Graph Header */}
              <div className="graph-header">
                <h2>Communication Activity</h2>
                <div className="graph-controls">
                  <div className="pattern-selector">
                    <span className="pattern-icon">📋</span>
                    <span>Auto Pattern</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="chevron">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  <div className="pattern-selector secondary">
                    <span>{selectedAlert.detection_algorithm?.toUpperCase() || 'DBSCAN'}</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="chevron">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  
                  {/* Rate Button */}
                  <div className="rate-section">
                    {alertRating ? (
                      <div className="rating-display" onClick={() => setShowRatingPopup(true)}>
                        <span className="rating-star">★</span>
                        <span className="rating-value">{alertRating}/10</span>
                      </div>
                    ) : (
                      <button className="rate-btn" onClick={() => setShowRatingPopup(true)}>
                        Rate
                      </button>
                    )}
                    
                    {showRatingPopup && (
                      <div className="rating-popup">
                        <div className="rating-popup-header">
                          <span>Rate this alert (1-10)</span>
                          <button onClick={() => setShowRatingPopup(false)}>×</button>
                        </div>
                        <div className="rating-numbers">
                          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                            <button
                              key={num}
                              className={`rating-num ${alertRating === num ? 'selected' : ''}`}
                              onClick={() => {
                                setAlertRating(num);
                                setShowRatingPopup(false);
                              }}
                            >
                              {num}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Graph Content */}
              <div className="graph-content">
                {graphLoading && (
                  <div className="graph-loading">
                    <div className="loader"></div>
                    <p>Analyzing patterns...</p>
                  </div>
                )}

                {graphError && (
                  <div className="graph-error">
                    <p>{graphError}</p>
                    <button onClick={() => handleAlertClick(selectedAlert, selectedAlert.category)}>
                      Retry
                    </button>
                  </div>
                )}

                {!graphLoading && !graphError && graphData && chartElements && (
                  <div className="chart-wrapper">
                    <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="activity-chart">
                      {/* Y-axis labels */}
                      {chartElements.yLabels.map((label, i) => (
                        <g key={i}>
                          <line
                            x1={padding.left}
                            y1={label.y}
                            x2={chartWidth - padding.right}
                            y2={label.y}
                            className="grid-line"
                          />
                          <text x={padding.left - 15} y={label.y + 4} className="axis-label y-label">
                            {label.value}
                          </text>
                        </g>
                      ))}

                      {/* X-axis labels */}
                      {chartElements.xLabels.map((label, i) => (
                        <text key={i} x={label.x} y={chartHeight - 15} className="axis-label x-label">
                          {label.label}
                        </text>
                      ))}

                      {/* Normal Pattern bracket */}
                      <g className="normal-pattern-indicator">
                        <line
                          x1={padding.left}
                          y1={padding.top - 20}
                          x2={chartElements.normalEndX}
                          y2={padding.top - 20}
                          className="bracket-line"
                        />
                        <line
                          x1={padding.left}
                          y1={padding.top - 25}
                          x2={padding.left}
                          y2={padding.top - 15}
                          className="bracket-line"
                        />
                        <line
                          x1={chartElements.normalEndX}
                          y1={padding.top - 25}
                          x2={chartElements.normalEndX}
                          y2={padding.top - 15}
                          className="bracket-line"
                        />
                        <text 
                          x={(padding.left + chartElements.normalEndX) / 2} 
                          y={padding.top - 30} 
                          className="normal-pattern-label"
                        >
                          Normal Pattern
                        </text>
                      </g>

                      {/* Area fill */}
                      <path
                        d={`${chartElements.pathD} L ${chartWidth - padding.right} ${padding.top + plotHeight} L ${padding.left} ${padding.top + plotHeight} Z`}
                        className="area-fill"
                      />

                      {/* Main line */}
                      <path d={chartElements.pathD} className="activity-line" />

                      {/* Data points */}
                      {chartElements.points.map((point, i) => (
                        <g key={i} className="data-point-group">
                          {/* Normal point */}
                          {!point.data.is_anomaly && (
                            <circle
                              cx={point.x}
                              cy={point.y}
                              r={5}
                              className="data-point normal"
                              onMouseEnter={() => setHoveredPoint(point)}
                              onMouseLeave={() => setHoveredPoint(null)}
                              onClick={() => handleDataPointClick(point.data)}
                            />
                          )}
                          
                          {/* Anomaly point */}
                          {point.data.is_anomaly && (
                            <g 
                              className="anomaly-point-group"
                              onMouseEnter={() => setHoveredPoint(point)}
                              onMouseLeave={() => setHoveredPoint(null)}
                              onClick={() => handleDataPointClick(point.data)}
                            >
                              <circle
                                cx={point.x}
                                cy={point.y}
                                r={12}
                                className="anomaly-glow"
                              />
                              <circle
                                cx={point.x}
                                cy={point.y}
                                r={6}
                                className="data-point anomaly"
                              />
                            </g>
                          )}
                        </g>
                      ))}

                      {/* Anomaly Popup */}
                      {hoveredPoint?.data?.is_anomaly && (
                        <g 
                          className="anomaly-popup"
                          transform={`translate(${Math.min(hoveredPoint.x, chartWidth - 200)}, ${hoveredPoint.y - 70})`}
                        >
                          <rect
                            x="-90"
                            y="-35"
                            width="180"
                            height="70"
                            rx="12"
                            className="popup-bg"
                          />
                          {/* Bell icon */}
                          <circle cx="-50" cy="0" r="20" className="bell-circle" />
                          <path
                            d="M-50 -8 C-50 -8 -56 -2 -56 4 C-56 8 -54 10 -50 10 C-46 10 -44 8 -44 4 C-44 -2 -50 -8 -50 -8"
                            className="bell-icon"
                          />
                          <circle cx="-50" cy="12" r="2" className="bell-icon" />
                          
                          {/* Text */}
                          <text x="10" y="-8" className="popup-title">ANOMALY DETECTED:</text>
                          <text x="10" y="12" className="popup-message">
                            {getAnomalyLabel(hoveredPoint.data.anomaly_type)}
                          </text>
                        </g>
                      )}

                      {/* Hover tooltip for normal points */}
                      {hoveredPoint && !hoveredPoint.data.is_anomaly && (
                        <g 
                          className="hover-tooltip"
                          transform={`translate(${hoveredPoint.x}, ${hoveredPoint.y - 40})`}
                        >
                          <rect
                            x="-60"
                            y="-25"
                            width="120"
                            height="30"
                            rx="6"
                            className="tooltip-bg"
                          />
                          <text x="0" y="-5" className="tooltip-text">
                            {hoveredPoint.data.email_count} emails
                          </text>
                        </g>
                      )}
                    </svg>
                  </div>
                )}

                {!graphLoading && !graphError && (!graphData || !graphData.data?.length) && (
                  <div className="graph-empty">
                    <p>No data available for this alert configuration</p>
                    <span>Try adjusting the alert's time window settings</span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Recent Alerts Section */}
      <div className="recent-alerts-section">
        <h2>Recent Alerts</h2>
        
        {recentAlerts.length === 0 ? (
          <div className="no-recent-alerts">
            <p>No alerts triggered recently</p>
          </div>
        ) : (
          <div className="recent-alerts-list">
            {recentAlerts.map((alert, i) => (
              <div key={i} className="recent-alert-item">
                <span className="alert-timestamp">{formatDateTime(alert.triggered_at)}</span>
                <span className="alert-indicator" style={{ backgroundColor: getSeverityColor(alert.severity) }}></span>
                <span className="alert-title">
                  {alert.anomaly_type === 'silence' ? 'Unusual Sentiment Change' : 
                   alert.anomaly_type === 'data_gap' ? 'Data Gap Detected' :
                   alert.anomaly_type === 'spike' ? 'Volume Spike Detected' :
                   'Alert Triggered'}:
                </span>
                <span className="alert-description">
                  {alert.trigger_reason || getAnomalyLabel(alert.anomaly_type)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Email Modal */}
      {showEmailModal && (
        <div className="modal-overlay" onClick={closeEmailModal}>
          <div className="email-modal email-modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                {selectedEmailDetail ? (
                  <>
                    <button className="back-btn" onClick={closeEmailDetail}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="15 18 9 12 15 6" />
                      </svg>
                      Back to list
                    </button>
                    <h2>Email Details</h2>
                  </>
                ) : (
                  <>
                    <h2>Emails at {selectedDataPoint && formatDateTime(selectedDataPoint.timestamp)}</h2>
                    {selectedAlert?.category === 'smart_ai' && (
                      <span className="smart-ai-filter-tag">
                        🤖 Semantic Search
                      </span>
                    )}
                    {selectedAlert?.entity_type && selectedAlert?.category !== 'smart_ai' && (
                      <span className="entity-filter-tag">
                        🏷️ {selectedAlert.entity_type}
                        {selectedAlert.entity_value && `: ${selectedAlert.entity_value}`}
                      </span>
                    )}
                    {selectedDataPoint?.is_anomaly && (
                      <span className="anomaly-tag">
                        🔴 {getAnomalyLabel(selectedDataPoint.anomaly_type)}
                      </span>
                    )}
                  </>
                )}
              </div>
              <button className="close-btn" onClick={closeEmailModal}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="modal-body">
              {/* Loading state for email detail */}
              {emailDetailLoading && (
                <div className="loading-state">
                  <div className="loader"></div>
                  <p>Loading email details...</p>
                </div>
              )}

              {/* Full Email Detail View */}
              {selectedEmailDetail && !emailDetailLoading && (
                <div className="email-detail-view">
                  {/* Email Header */}
                  <div className="email-detail-header">
                    <h3 className="email-detail-subject">{selectedEmailDetail.subject || 'No Subject'}</h3>
                    
                    <div className="email-detail-meta">
                      <div className="meta-row">
                        <span className="meta-label">From:</span>
                        <span className="meta-value">{selectedEmailDetail.sender || 'Unknown'}</span>
                      </div>
                      
                      {selectedEmailDetail.recipients && selectedEmailDetail.recipients.length > 0 && (
                        <div className="meta-row">
                          <span className="meta-label">To:</span>
                          <span className="meta-value">{selectedEmailDetail.recipients.join(', ')}</span>
                        </div>
                      )}
                      
                      {selectedEmailDetail.cc && selectedEmailDetail.cc.length > 0 && (
                        <div className="meta-row">
                          <span className="meta-label">CC:</span>
                          <span className="meta-value">{selectedEmailDetail.cc.join(', ')}</span>
                        </div>
                      )}
                      
                      <div className="meta-row">
                        <span className="meta-label">Date:</span>
                        <span className="meta-value">{formatFullDate(selectedEmailDetail.date)}</span>
                      </div>
                      
                      {selectedEmailDetail.message_id && (
                        <div className="meta-row">
                          <span className="meta-label">Message ID:</span>
                          <span className="meta-value message-id">{selectedEmailDetail.message_id}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Entities Section */}
                  {selectedEmailDetail.entities && selectedEmailDetail.entities.length > 0 && (
                    <div className="email-detail-entities">
                      <h4>📍 Extracted Entities ({selectedEmailDetail.entities.length})</h4>
                      <div className="entities-grid">
                        {Object.entries(
                          selectedEmailDetail.entities.reduce((acc, entity) => {
                            if (!acc[entity.type]) acc[entity.type] = [];
                            acc[entity.type].push(entity);
                            return acc;
                          }, {})
                        ).map(([type, entities]) => (
                          <div key={type} className="entity-type-group">
                            <div className="entity-type-header" style={{ borderColor: getEntityColor(type) }}>
                              <span className="entity-type-dot" style={{ backgroundColor: getEntityColor(type) }}></span>
                              {type} ({entities.length})
                            </div>
                            <div className="entity-type-items">
                              {entities.slice(0, 15).map((entity, idx) => (
                                <span 
                                  key={idx} 
                                  className="entity-item"
                                  style={{ 
                                    backgroundColor: `${getEntityColor(type)}20`,
                                    borderColor: `${getEntityColor(type)}50`,
                                    color: getEntityColor(type)
                                  }}
                                  title={entity.sentence || entity.text}
                                >
                                  {entity.text}
                                </span>
                              ))}
                              {entities.length > 15 && (
                                <span className="entity-more-count">+{entities.length - 15} more</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Email Body */}
                  <div className="email-detail-body">
                    <h4>📧 Email Body</h4>
                    <div className="email-body-content">
                      {selectedEmailDetail.body_html ? (
                        <div 
                          className="email-body-html"
                          dangerouslySetInnerHTML={{ __html: selectedEmailDetail.body_html }}
                        />
                      ) : (
                        <pre className="email-body-text">{selectedEmailDetail.body || 'No content'}</pre>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Email List View */}
              {!selectedEmailDetail && !emailDetailLoading && (
                <>
                  {emailsLoading ? (
                    <div className="loading-state">
                      <div className="loader"></div>
                      <p>Loading emails...</p>
                    </div>
                  ) : emails.length === 0 ? (
                    <div className="empty-state">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                        <polyline points="22,6 12,13 2,6" />
                      </svg>
                      <p>No emails found for this time period</p>
                    </div>
                  ) : (
                    <div className="emails-list">
                      <div className="emails-count">{emails.length} email(s) found - Click to view full details</div>
                      {emails.map((email, i) => (
                        <div 
                          key={i} 
                          className="email-item email-item-clickable"
                          onClick={() => handleViewFullEmail(email.id)}
                        >
                          <div className="email-header">
                            <span className="email-subject">{email.subject || '(No Subject)'}</span>
                            <div className="email-header-right">
                              {email.relevance_score && (
                                <span className="relevance-badge" style={{
                                  backgroundColor: email.relevance_score >= 0.8 ? '#10b981' : 
                                                   email.relevance_score >= 0.6 ? '#f59e0b' : '#ef4444'
                                }}>
                                  {(email.relevance_score * 100).toFixed(0)}% match
                                </span>
                              )}
                              <span className="email-date">
                                {email.date && formatDateTime(email.date)}
                              </span>
                            </div>
                          </div>
                          <div className="email-meta">
                            <span><strong>From:</strong> {email.sender || 'Unknown'}</span>
                            <span>
                              <strong>To:</strong> {email.recipients?.slice(0, 2).join(', ') || 'Unknown'}
                              {email.recipients?.length > 2 && ` +${email.recipients.length - 2} more`}
                            </span>
                          </div>
                          {email.body_preview && (
                            <div className="email-preview">{email.body_preview}</div>
                          )}
                          {email.entities?.length > 0 && (
                            <div className="email-entities">
                              {email.entities.slice(0, 5).map((ent, j) => (
                                <span key={j} className="entity-chip">{ent.type}: {ent.text}</span>
                              ))}
                              {email.entities.length > 5 && (
                                <span className="entity-more">+{email.entities.length - 5}</span>
                              )}
                            </div>
                          )}
                          <div className="view-full-hint">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                              <polyline points="15 3 21 3 21 9" />
                              <line x1="10" y1="14" x2="21" y2="3" />
                            </svg>
                            Click to view full email
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AlertsDashboard;
