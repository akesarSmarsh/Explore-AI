import { useState } from 'react';
import { searchAPI, emailAPI } from '../api/apiService';
import './Search.css';

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

// Preset time ranges for quick selection
const TIME_RANGES = [
  { label: 'All Time', value: 'all' },
  { label: 'Last 24 Hours', value: '24h' },
  { label: 'Last 7 Days', value: '7d' },
  { label: 'Last 30 Days', value: '30d' },
  { label: 'Last 90 Days', value: '90d' },
  { label: 'Custom Range', value: 'custom' },
];

function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);
  
  // Date filter state
  const [timeRange, setTimeRange] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  
  // Email detail modal state
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailError, setEmailError] = useState(null);

  // Calculate date range based on preset selection
  const getDateRange = () => {
    const now = new Date();
    let fromDate = null;
    let toDate = null;

    switch (timeRange) {
      case '24h':
        fromDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      case '7d':
        fromDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30d':
        fromDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case '90d':
        fromDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        break;
      case 'custom':
        fromDate = dateFrom ? new Date(dateFrom) : null;
        toDate = dateTo ? new Date(dateTo) : null;
        break;
      default:
        // 'all' - no date filter
        break;
    }

    return {
      from: fromDate ? fromDate.toISOString() : null,
      to: toDate ? toDate.toISOString() : null,
    };
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    
    // Clear any previous error immediately
    setError(null);
    
    if (!query.trim() || query.trim().length < 3) {
      setError('Please enter at least 3 characters');
      return;
    }

    setLoading(true);
    setSearched(true);
    setResults([]); // Clear previous results while loading

    try {
      const { from, to } = getDateRange();
      const response = await searchAPI.semantic(query.trim(), 20, from, to);
      setResults(response.results || []);
    } catch (err) {
      console.error('Search error:', err);
      setError(err.response?.data?.detail || 'Failed to perform search. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTimeRangeChange = (value) => {
    setTimeRange(value);
    if (value !== 'custom') {
      setDateFrom('');
      setDateTo('');
    }
  };

  const clearFilters = () => {
    setTimeRange('all');
    setDateFrom('');
    setDateTo('');
  };

  const handleOpenEmail = async (emailId) => {
    setEmailLoading(true);
    setEmailError(null);
    
    try {
      const emailData = await emailAPI.get(emailId);
      setSelectedEmail(emailData);
    } catch (err) {
      console.error('Fetch email error:', err);
      setEmailError(err.response?.data?.detail || 'Failed to load email details');
    } finally {
      setEmailLoading(false);
    }
  };

  const handleCloseEmail = () => {
    setSelectedEmail(null);
    setEmailError(null);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

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

  const getRelevanceColor = (score) => {
    if (score >= 0.8) return '#10b981';
    if (score >= 0.6) return '#f59e0b';
    return '#ef4444';
  };

  const getEntityColor = (type) => {
    return ENTITY_COLORS[type] || '#6b7280';
  };

  return (
    <div className="search-container">
      <div className="search-header">
        <h1>Semantic Search</h1>
        <p className="search-description">
          Search emails using natural language. Find semantically similar content, not just keyword matches.
        </p>
      </div>

      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., emails about financial irregularities, discussions about quarterly reports..."
            className="search-input"
          />
          <button 
            type="button" 
            className={`filter-toggle-btn ${showFilters ? 'active' : ''} ${timeRange !== 'all' ? 'has-filters' : ''}`}
            onClick={() => setShowFilters(!showFilters)}
            title="Toggle filters"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
            </svg>
            {timeRange !== 'all' && <span className="filter-indicator"></span>}
          </button>
          <button type="submit" className="search-button" disabled={loading}>
            {loading ? (
              <span className="loader"></span>
            ) : (
              'Search'
            )}
          </button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="filter-panel">
            <div className="filter-header">
              <h3>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                Time Range Filter
              </h3>
              {timeRange !== 'all' && (
                <button type="button" className="clear-filters-btn" onClick={clearFilters}>
                  Clear Filters
                </button>
              )}
            </div>

            <div className="time-range-options">
              {TIME_RANGES.map((range) => (
                <button
                  key={range.value}
                  type="button"
                  className={`time-range-btn ${timeRange === range.value ? 'active' : ''}`}
                  onClick={() => handleTimeRangeChange(range.value)}
                >
                  {range.label}
                </button>
              ))}
            </div>

            {timeRange === 'custom' && (
              <div className="custom-date-range">
                <div className="date-input-group">
                  <label>From</label>
                  <input
                    type="datetime-local"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="date-input"
                  />
                </div>
                <div className="date-input-group">
                  <label>To</label>
                  <input
                    type="datetime-local"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="date-input"
                  />
                </div>
              </div>
            )}

            {timeRange !== 'all' && (
              <div className="active-filter-summary">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                {timeRange === 'custom' 
                  ? `Custom: ${dateFrom ? new Date(dateFrom).toLocaleDateString() : 'Any'} - ${dateTo ? new Date(dateTo).toLocaleDateString() : 'Now'}`
                  : `Showing results from ${TIME_RANGES.find(r => r.value === timeRange)?.label.toLowerCase()}`
                }
              </div>
            )}
          </div>
        )}
      </form>

      {error && (
        <div className="error-message">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      {searched && !loading && results.length === 0 && !error && (
        <div className="no-results">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <p>No results found for "{query}"</p>
          <span>Try different keywords or broader search terms</span>
        </div>
      )}

      {results.length > 0 && (
        <div className="results-container">
          <div className="results-header">
            <h2>Search Results</h2>
            <span className="results-count">{results.length} results found</span>
          </div>

          <div className="results-list">
            {results.map((result, index) => (
              <div 
                key={result.email_id || index} 
                className="result-card"
                onClick={() => handleOpenEmail(result.email_id)}
              >
                <div className="result-header">
                  <h3 className="result-subject">{result.subject || 'No Subject'}</h3>
                  <div 
                    className="relevance-badge"
                    style={{ backgroundColor: getRelevanceColor(result.relevance_score) }}
                  >
                    {(result.relevance_score * 100).toFixed(0)}% match
                  </div>
                </div>

                <div className="result-meta">
                  <span className="result-sender">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    {result.sender || 'Unknown'}
                  </span>
                  <span className="result-date">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                      <line x1="16" y1="2" x2="16" y2="6" />
                      <line x1="8" y1="2" x2="8" y2="6" />
                      <line x1="3" y1="10" x2="21" y2="10" />
                    </svg>
                    {formatDate(result.date)}
                  </span>
                </div>

                {result.snippet && (
                  <p className="result-snippet">{result.snippet}</p>
                )}

                {result.matched_entities && result.matched_entities.length > 0 && (
                  <div className="result-entities">
                    {result.matched_entities.slice(0, 5).map((entity, i) => (
                      <span key={i} className="entity-tag">{entity}</span>
                    ))}
                    {result.matched_entities.length > 5 && (
                      <span className="entity-more">+{result.matched_entities.length - 5} more</span>
                    )}
                  </div>
                )}

                <div className="click-hint">
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
        </div>
      )}

      {/* Email Detail Modal */}
      {(selectedEmail || emailLoading || emailError) && (
        <div className="email-modal-overlay" onClick={handleCloseEmail}>
          <div className="email-modal" onClick={(e) => e.stopPropagation()}>
            <div className="email-modal-header">
              <h2>Email Details</h2>
              <button className="close-btn" onClick={handleCloseEmail}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            {emailLoading && (
              <div className="email-loading">
                <div className="email-loader"></div>
                <p>Loading email...</p>
              </div>
            )}

            {emailError && (
              <div className="email-error">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <p>{emailError}</p>
              </div>
            )}

            {selectedEmail && !emailLoading && (
              <div className="email-content">
                {/* Email Header */}
                <div className="email-header-section">
                  <h3 className="email-subject">{selectedEmail.subject || 'No Subject'}</h3>
                  
                  <div className="email-meta-grid">
                    <div className="meta-row">
                      <span className="meta-label">From:</span>
                      <span className="meta-value sender-value">{selectedEmail.sender || 'Unknown'}</span>
                    </div>
                    
                    {selectedEmail.recipients && selectedEmail.recipients.length > 0 && (
                      <div className="meta-row">
                        <span className="meta-label">To:</span>
                        <span className="meta-value">{selectedEmail.recipients.join(', ')}</span>
                      </div>
                    )}
                    
                    {selectedEmail.cc && selectedEmail.cc.length > 0 && (
                      <div className="meta-row">
                        <span className="meta-label">CC:</span>
                        <span className="meta-value">{selectedEmail.cc.join(', ')}</span>
                      </div>
                    )}
                    
                    <div className="meta-row">
                      <span className="meta-label">Date:</span>
                      <span className="meta-value">{formatFullDate(selectedEmail.date)}</span>
                    </div>
                    
                    {selectedEmail.message_id && (
                      <div className="meta-row">
                        <span className="meta-label">Message ID:</span>
                        <span className="meta-value message-id">{selectedEmail.message_id}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Entities Section */}
                {selectedEmail.entities && selectedEmail.entities.length > 0 && (
                  <div className="email-entities-section">
                    <h4>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                        <line x1="7" y1="7" x2="7.01" y2="7" />
                      </svg>
                      Extracted Entities ({selectedEmail.entities.length})
                    </h4>
                    <div className="entities-grid">
                      {/* Group entities by type */}
                      {Object.entries(
                        selectedEmail.entities.reduce((acc, entity) => {
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
                            {entities.slice(0, 10).map((entity, idx) => (
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
                            {entities.length > 10 && (
                              <span className="entity-more-count">+{entities.length - 10} more</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Alerts Section */}
                {selectedEmail.alerts && selectedEmail.alerts.length > 0 && (
                  <div className="email-alerts-section">
                    <h4>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                        <line x1="12" y1="9" x2="12" y2="13" />
                        <line x1="12" y1="17" x2="12.01" y2="17" />
                      </svg>
                      Triggered Alerts ({selectedEmail.alerts.length})
                    </h4>
                    <div className="alerts-list">
                      {selectedEmail.alerts.map((alert, idx) => (
                        <div key={idx} className="alert-item">
                          <span className={`alert-severity ${alert.severity}`}>{alert.severity}</span>
                          <span className="alert-name">{alert.rule_name}</span>
                          {alert.matched_entity && (
                            <span className="alert-matched">Matched: {alert.matched_entity}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Email Body */}
                <div className="email-body-section">
                  <h4>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                    Email Body
                  </h4>
                  <div className="email-body-content">
                    {selectedEmail.body_html ? (
                      <div 
                        className="email-body-html"
                        dangerouslySetInnerHTML={{ __html: selectedEmail.body_html }}
                      />
                    ) : (
                      <pre className="email-body-text">{selectedEmail.body || 'No content'}</pre>
                    )}
                  </div>
                </div>

                {/* Similar Emails */}
                {selectedEmail.similar_emails && selectedEmail.similar_emails.length > 0 && (
                  <div className="similar-emails-section">
                    <h4>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </svg>
                      Similar Emails ({selectedEmail.similar_emails.length})
                    </h4>
                    <div className="similar-emails-list">
                      {selectedEmail.similar_emails.slice(0, 5).map((emailId, idx) => (
                        <button 
                          key={idx} 
                          className="similar-email-btn"
                          onClick={() => handleOpenEmail(emailId)}
                        >
                          View Email #{idx + 1}
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="9 18 15 12 9 6" />
                          </svg>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Search;
