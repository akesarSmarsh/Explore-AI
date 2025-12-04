import { useState, useEffect, useCallback } from 'react';
import { nerAPI, emailAPI } from '../api/apiService';
import './NERWordCloud.css';

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
  NORP: '#38bdf8',
  FAC: '#fb7185',
  LAW: '#a3e635',
  LANGUAGE: '#e879f9',
  TIME: '#22d3ee',
  QUANTITY: '#fcd34d',
  ORDINAL: '#94a3b8',
  WORK_OF_ART: '#f0abfc',
  // Phrase types
  NOUN_PHRASE: '#06b6d4',
  VERB_PHRASE: '#8b5cf6',
  ACTION: '#ec4899',
};

const ENTITY_TYPES = [
  'PERSON', 'ORG', 'GPE', 'MONEY', 'DATE', 'CARDINAL', 
  'PERCENT', 'LOC', 'PRODUCT', 'EVENT'
];

const PHRASE_TYPES = [
  { value: 'all', label: 'All Phrases' },
  { value: 'noun_phrases', label: 'Noun Phrases' },
  { value: 'verb_phrases', label: 'Verb Phrases' },
  { value: 'actions', label: 'Actions' },
];

function NERWordCloud() {
  // View mode: 'entities' or 'phrases'
  const [viewMode, setViewMode] = useState('entities');
  
  // Entity state
  const [wordcloudData, setWordcloudData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [limit, setLimit] = useState(100);
  const [breakdown, setBreakdown] = useState(null);
  
  // Phrase state
  const [phrasesData, setPhrasesData] = useState(null);
  const [phrasesLoading, setPhrasesLoading] = useState(false);
  const [phrasesError, setPhrasesError] = useState(null);
  const [selectedPhraseType, setSelectedPhraseType] = useState('all');
  
  // Entity emails modal state
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [entityEmails, setEntityEmails] = useState(null);
  const [emailsLoading, setEmailsLoading] = useState(false);
  const [emailsError, setEmailsError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  
  // Email detail modal state
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [emailDetailLoading, setEmailDetailLoading] = useState(false);

  const fetchWordcloud = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const entityTypes = selectedTypes.length > 0 ? selectedTypes.join(',') : null;
      const response = await nerAPI.getWordcloud(entityTypes, limit, 1);
      setWordcloudData(response.entities || []);
    } catch (err) {
      console.error('Wordcloud error:', err);
      setError(err.response?.data?.detail || 'Failed to load word cloud data');
    } finally {
      setLoading(false);
    }
  }, [selectedTypes, limit]);

  const fetchBreakdown = useCallback(async () => {
    try {
      const response = await nerAPI.getBreakdown();
      setBreakdown(response);
    } catch (err) {
      console.error('Breakdown error:', err);
    }
  }, []);

  const fetchPhrases = useCallback(async () => {
    setPhrasesLoading(true);
    setPhrasesError(null);

    try {
      const response = await nerAPI.getPhrasesWordcloud(selectedPhraseType, limit);
      setPhrasesData(response);
    } catch (err) {
      console.error('Phrases error:', err);
      setPhrasesError(err.response?.data?.detail || 'Failed to load phrases data');
    } finally {
      setPhrasesLoading(false);
    }
  }, [selectedPhraseType, limit]);

  useEffect(() => {
    if (viewMode === 'entities') {
      fetchWordcloud();
      fetchBreakdown();
    } else {
      fetchPhrases();
    }
  }, [viewMode, fetchWordcloud, fetchBreakdown, fetchPhrases]);

  const toggleEntityType = (type) => {
    setSelectedTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const getWordSize = (weight) => {
    const minSize = 14;
    const maxSize = 64;
    return minSize + (weight * (maxSize - minSize));
  };

  const getWordColor = (type) => {
    return ENTITY_COLORS[type] || '#a1a1aa';
  };

  const shuffleArray = (array) => {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  };

  // Handle entity click - fetch emails containing this entity
  const handleEntityClick = async (entity) => {
    setSelectedEntity(entity);
    setCurrentPage(1);
    setEmailsLoading(true);
    setEmailsError(null);
    setEntityEmails(null);

    try {
      const response = await nerAPI.getEmailsByEntity(entity.text, entity.type, 1, 10);
      setEntityEmails(response);
    } catch (err) {
      console.error('Fetch entity emails error:', err);
      setEmailsError(err.response?.data?.detail || 'Failed to load emails');
    } finally {
      setEmailsLoading(false);
    }
  };

  // Handle phrase click - fetch emails containing this phrase
  const handlePhraseClick = async (phrase) => {
    setSelectedEntity({ ...phrase, isPhrase: true });
    setCurrentPage(1);
    setEmailsLoading(true);
    setEmailsError(null);
    setEntityEmails(null);

    try {
      const response = await nerAPI.getEmailsByPhrase(phrase.text, phrase.type, 1, 10);
      // Transform response to match entity emails format
      setEntityEmails({
        ...response,
        total_pages: response.total_pages,
        emails: response.emails.map(email => ({
          ...email,
          matched_entities: email.context_snippet ? [{ sentence: email.context_snippet }] : [],
          total_matched: email.occurrence_count
        }))
      });
    } catch (err) {
      console.error('Fetch phrase emails error:', err);
      setEmailsError(err.response?.data?.detail || 'Failed to load emails');
    } finally {
      setEmailsLoading(false);
    }
  };

  // Handle pagination
  const handlePageChange = async (newPage) => {
    if (!selectedEntity || newPage < 1 || (entityEmails && newPage > entityEmails.total_pages)) return;
    
    setCurrentPage(newPage);
    setEmailsLoading(true);

    try {
      let response;
      if (selectedEntity.isPhrase) {
        // Phrase pagination
        response = await nerAPI.getEmailsByPhrase(selectedEntity.text, selectedEntity.type, newPage, 10);
        setEntityEmails({
          ...response,
          total_pages: response.total_pages,
          emails: response.emails.map(email => ({
            ...email,
            matched_entities: email.context_snippet ? [{ sentence: email.context_snippet }] : [],
            total_matched: email.occurrence_count
          }))
        });
      } else {
        // Entity pagination
        response = await nerAPI.getEmailsByEntity(selectedEntity.text, selectedEntity.type, newPage, 10);
        setEntityEmails(response);
      }
    } catch (err) {
      console.error('Fetch page error:', err);
    } finally {
      setEmailsLoading(false);
    }
  };

  // Close entity modal
  const closeEntityModal = () => {
    setSelectedEntity(null);
    setEntityEmails(null);
    setEmailsError(null);
    setCurrentPage(1);
  };

  // Open email detail
  const handleOpenEmail = async (emailId) => {
    setEmailDetailLoading(true);
    try {
      const emailData = await emailAPI.get(emailId);
      setSelectedEmail(emailData);
    } catch (err) {
      console.error('Fetch email error:', err);
      alert('Failed to load email details');
    } finally {
      setEmailDetailLoading(false);
    }
  };

  // Close email detail
  const closeEmailDetail = () => {
    setSelectedEmail(null);
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

  // Get combined phrases for word cloud
  const getCombinedPhrases = () => {
    if (!phrasesData) return [];
    
    if (selectedPhraseType === 'all') {
      // Combine all phrase types
      const all = [
        ...(phrasesData.noun_phrases || []),
        ...(phrasesData.verb_phrases || []),
        ...(phrasesData.actions || []),
      ];
      return all;
    }
    
    return phrasesData.phrases || [];
  };

  return (
    <div className="ner-container">
      <div className="ner-header">
        <h1>Named Entity Recognition & Phrases</h1>
        <p className="ner-description">
          Visual representation of entities and phrases extracted from emails. Click on any item to see related emails.
        </p>
      </div>

      {/* View Mode Toggle */}
      <div className="view-mode-toggle">
        <button 
          className={`mode-btn ${viewMode === 'entities' ? 'active' : ''}`}
          onClick={() => setViewMode('entities')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
            <line x1="7" y1="7" x2="7.01" y2="7" />
          </svg>
          Entities
        </button>
        <button 
          className={`mode-btn ${viewMode === 'phrases' ? 'active' : ''}`}
          onClick={() => setViewMode('phrases')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Phrases & Verbs
        </button>
      </div>

      {/* Entity View */}
      {viewMode === 'entities' && (
        <>
          {/* Entity Type Filters */}
          <div className="filter-section">
            <div className="filter-header">
              <h3>Filter by Entity Type</h3>
              {selectedTypes.length > 0 && (
                <button 
                  className="clear-filters"
                  onClick={() => setSelectedTypes([])}
                >
                  Clear All
                </button>
              )}
            </div>
            <div className="entity-filters">
              {ENTITY_TYPES.map(type => (
                <button
                  key={type}
                  className={`filter-chip ${selectedTypes.includes(type) ? 'active' : ''}`}
                  onClick={() => toggleEntityType(type)}
                  style={{
                    '--chip-color': ENTITY_COLORS[type],
                    borderColor: selectedTypes.includes(type) ? ENTITY_COLORS[type] : 'transparent',
                    backgroundColor: selectedTypes.includes(type) 
                      ? `${ENTITY_COLORS[type]}20` 
                      : '#313244'
                  }}
                >
                  <span 
                    className="chip-dot" 
                    style={{ backgroundColor: ENTITY_COLORS[type] }}
                  ></span>
                  {type}
                </button>
              ))}
            </div>

            <div className="limit-control">
              <label>Max Entities:</label>
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
              </select>
              <button className="refresh-btn" onClick={fetchWordcloud}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                  <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
                  <path d="M21 21v-5h-5" />
                </svg>
                Refresh
              </button>
            </div>
          </div>

          {/* Entity Breakdown Stats */}
          {breakdown && breakdown.breakdown && (
            <div className="breakdown-section">
              <h3>Entity Distribution</h3>
              <div className="breakdown-bars">
                {breakdown.breakdown.slice(0, 8).map((item, index) => (
                  <div key={index} className="breakdown-item">
                    <div className="breakdown-label">
                      <span 
                        className="type-indicator"
                        style={{ backgroundColor: ENTITY_COLORS[item.entity_type] || '#6b7280' }}
                      ></span>
                      <span className="type-name">{item.entity_type}</span>
                      <span className="type-count">{item.total_count.toLocaleString()}</span>
                    </div>
                    <div className="breakdown-bar-container">
                      <div 
                        className="breakdown-bar"
                        style={{ 
                          width: `${item.percentage}%`,
                          backgroundColor: ENTITY_COLORS[item.entity_type] || '#6b7280'
                        }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entity Word Cloud */}
          <div className="wordcloud-section">
            {loading && (
              <div className="loading-state">
                <div className="cloud-loader"></div>
                <p>Loading entities...</p>
              </div>
            )}

            {error && (
              <div className="error-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <p>{error}</p>
                <button onClick={fetchWordcloud}>Retry</button>
              </div>
            )}

            {!loading && !error && wordcloudData.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M8 12h8" />
                </svg>
                <p>No entities found</p>
                <span>Try adjusting filters or processing more emails</span>
              </div>
            )}

            {!loading && !error && wordcloudData.length > 0 && (
              <div className="wordcloud-container">
                <div className="wordcloud">
                  {shuffleArray(wordcloudData).map((entity, index) => (
                    <span
                      key={`${entity.text}-${index}`}
                      className="word clickable"
                      style={{
                        fontSize: `${getWordSize(entity.weight)}px`,
                        color: getWordColor(entity.type),
                        animationDelay: `${index * 20}ms`,
                      }}
                      title={`Click to see emails containing "${entity.text}" (${entity.type}): ${entity.count} mentions`}
                      onClick={() => handleEntityClick(entity)}
                    >
                      {entity.text}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Entity Legend */}
          <div className="legend-section">
            <h4>Entity Types</h4>
            <div className="legend-items">
              {Object.entries(ENTITY_COLORS).slice(0, 10).map(([type, color]) => (
                <div key={type} className="legend-item">
                  <span className="legend-dot" style={{ backgroundColor: color }}></span>
                  <span className="legend-label">{type}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Phrases View */}
      {viewMode === 'phrases' && (
        <>
          {/* Phrase Type Filters */}
          <div className="filter-section">
            <div className="filter-header">
              <h3>Phrase Type</h3>
            </div>
            <div className="entity-filters">
              {PHRASE_TYPES.map(type => (
                <button
                  key={type.value}
                  className={`filter-chip ${selectedPhraseType === type.value ? 'active' : ''}`}
                  onClick={() => setSelectedPhraseType(type.value)}
                  style={{
                    '--chip-color': type.value === 'noun_phrases' ? ENTITY_COLORS.NOUN_PHRASE :
                                    type.value === 'verb_phrases' ? ENTITY_COLORS.VERB_PHRASE :
                                    type.value === 'actions' ? ENTITY_COLORS.ACTION : '#06b6d4',
                    borderColor: selectedPhraseType === type.value ? 
                      (type.value === 'noun_phrases' ? ENTITY_COLORS.NOUN_PHRASE :
                       type.value === 'verb_phrases' ? ENTITY_COLORS.VERB_PHRASE :
                       type.value === 'actions' ? ENTITY_COLORS.ACTION : '#06b6d4') : 'transparent',
                    backgroundColor: selectedPhraseType === type.value 
                      ? `${type.value === 'noun_phrases' ? ENTITY_COLORS.NOUN_PHRASE :
                          type.value === 'verb_phrases' ? ENTITY_COLORS.VERB_PHRASE :
                          type.value === 'actions' ? ENTITY_COLORS.ACTION : '#06b6d4'}20` 
                      : '#313244'
                  }}
                >
                  <span 
                    className="chip-dot" 
                    style={{ 
                      backgroundColor: type.value === 'noun_phrases' ? ENTITY_COLORS.NOUN_PHRASE :
                                       type.value === 'verb_phrases' ? ENTITY_COLORS.VERB_PHRASE :
                                       type.value === 'actions' ? ENTITY_COLORS.ACTION : '#06b6d4'
                    }}
                  ></span>
                  {type.label}
                </button>
              ))}
            </div>

            <div className="limit-control">
              <label>Max Phrases:</label>
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
              </select>
              <button className="refresh-btn" onClick={fetchPhrases}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                  <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
                  <path d="M21 21v-5h-5" />
                </svg>
                Refresh
              </button>
            </div>
          </div>

          {/* Phrases Word Cloud */}
          <div className="wordcloud-section">
            {phrasesLoading && (
              <div className="loading-state">
                <div className="cloud-loader"></div>
                <p>Extracting phrases from emails...</p>
                <span className="loading-hint">This may take a moment for large datasets</span>
              </div>
            )}

            {phrasesError && (
              <div className="error-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <p>{phrasesError}</p>
                <button onClick={fetchPhrases}>Retry</button>
              </div>
            )}

            {!phrasesLoading && !phrasesError && getCombinedPhrases().length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M8 12h8" />
                </svg>
                <p>No phrases found</p>
                <span>Try processing more emails or changing the phrase type</span>
              </div>
            )}

            {!phrasesLoading && !phrasesError && getCombinedPhrases().length > 0 && (
              <div className="wordcloud-container">
                <div className="wordcloud">
                  {shuffleArray(getCombinedPhrases()).map((phrase, index) => (
                    <span
                      key={`${phrase.text}-${index}`}
                      className="word phrase-word clickable"
                      style={{
                        fontSize: `${getWordSize(phrase.weight)}px`,
                        color: getWordColor(phrase.type),
                        animationDelay: `${index * 20}ms`,
                      }}
                      title={`Click to see emails containing "${phrase.text}" (${phrase.type}): ${phrase.count} occurrences`}
                      onClick={() => handlePhraseClick(phrase)}
                    >
                      {phrase.text}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Phrase Legend */}
          <div className="legend-section">
            <h4>Phrase Types</h4>
            <div className="legend-items">
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: ENTITY_COLORS.NOUN_PHRASE }}></span>
                <span className="legend-label">Noun Phrases</span>
                <span className="legend-desc">- Important noun chunks (e.g., "quarterly report")</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: ENTITY_COLORS.VERB_PHRASE }}></span>
                <span className="legend-label">Verb Phrases</span>
                <span className="legend-desc">- Verb combinations (e.g., "has been investigating")</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: ENTITY_COLORS.ACTION }}></span>
                <span className="legend-label">Actions</span>
                <span className="legend-desc">- Subject-verb-object patterns (e.g., "team reviewed documents")</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Entity Emails Modal */}
      {selectedEntity && (
        <div className="entity-modal-overlay" onClick={closeEntityModal}>
          <div className="entity-modal" onClick={(e) => e.stopPropagation()}>
            <div className="entity-modal-header">
              <div className="entity-modal-title">
                <span 
                  className="entity-badge"
                  style={{ 
                    backgroundColor: `${getWordColor(selectedEntity.type)}20`,
                    color: getWordColor(selectedEntity.type),
                    borderColor: getWordColor(selectedEntity.type)
                  }}
                >
                  {selectedEntity.type}
                </span>
                <h2>"{selectedEntity.text}"</h2>
                <span className="entity-count">{selectedEntity.count} mentions</span>
              </div>
              <button className="close-btn" onClick={closeEntityModal}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="entity-modal-content">
              {emailsLoading && (
                <div className="emails-loading">
                  <div className="email-loader"></div>
                  <p>Loading emails...</p>
                </div>
              )}

              {emailsError && (
                <div className="emails-error">
                  <p>{emailsError}</p>
                </div>
              )}

              {entityEmails && !emailsLoading && (
                <>
                  <div className="emails-summary">
                    Found in <strong>{entityEmails.total}</strong> email{entityEmails.total !== 1 ? 's' : ''}
                  </div>

                  <div className="entity-emails-list">
                    {entityEmails.emails.map((email) => (
                      <div 
                        key={email.id} 
                        className="entity-email-card"
                        onClick={() => handleOpenEmail(email.id)}
                      >
                        <div className="email-card-header">
                          <h4>{email.subject || 'No Subject'}</h4>
                          <span className="email-date">{formatDate(email.date)}</span>
                        </div>
                        <div className="email-card-sender">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                            <circle cx="12" cy="7" r="4" />
                          </svg>
                          {email.sender || 'Unknown'}
                        </div>
                        {email.preview && (
                          <p className="email-card-preview">{email.preview}</p>
                        )}
                        {email.matched_entities && email.matched_entities.length > 0 && (
                          <div className="matched-context">
                            <span className="context-label">Context:</span>
                            {email.matched_entities[0].sentence && (
                              <span className="context-text">
                                "...{email.matched_entities[0].sentence.slice(0, 150)}..."
                              </span>
                            )}
                          </div>
                        )}
                        <div className="email-card-footer">
                          <span className="matched-count">
                            {email.total_matched} occurrence{email.total_matched !== 1 ? 's' : ''} in this email
                          </span>
                          <span className="view-email-hint">Click to view →</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pagination */}
                  {entityEmails.total_pages > 1 && (
                    <div className="pagination">
                      <button 
                        className="page-btn"
                        disabled={currentPage === 1}
                        onClick={() => handlePageChange(currentPage - 1)}
                      >
                        ← Previous
                      </button>
                      <span className="page-info">
                        Page {currentPage} of {entityEmails.total_pages}
                      </span>
                      <button 
                        className="page-btn"
                        disabled={currentPage === entityEmails.total_pages}
                        onClick={() => handlePageChange(currentPage + 1)}
                      >
                        Next →
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Email Detail Modal */}
      {selectedEmail && (
        <div className="email-detail-overlay" onClick={closeEmailDetail}>
          <div className="email-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="email-detail-header">
              <h2>Email Details</h2>
              <button className="close-btn" onClick={closeEmailDetail}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="email-detail-content">
              <h3>{selectedEmail.subject || 'No Subject'}</h3>
              <div className="email-meta">
                <p><strong>From:</strong> {selectedEmail.sender}</p>
                <p><strong>To:</strong> {selectedEmail.recipients?.join(', ') || 'N/A'}</p>
                <p><strong>Date:</strong> {formatDate(selectedEmail.date)}</p>
              </div>
              
              {selectedEmail.entities && selectedEmail.entities.length > 0 && (
                <div className="email-entities">
                  <h4>Entities ({selectedEmail.entities.length})</h4>
                  <div className="entities-tags">
                    {selectedEmail.entities.slice(0, 20).map((entity, idx) => (
                      <span 
                        key={idx}
                        className="entity-tag"
                        style={{
                          backgroundColor: `${getWordColor(entity.type)}20`,
                          color: getWordColor(entity.type),
                          borderColor: `${getWordColor(entity.type)}50`
                        }}
                      >
                        {entity.text} <small>({entity.type})</small>
                      </span>
                    ))}
                    {selectedEmail.entities.length > 20 && (
                      <span className="more-entities">+{selectedEmail.entities.length - 20} more</span>
                    )}
                  </div>
                </div>
              )}
              
              <div className="email-body">
                <h4>Content</h4>
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
          </div>
        </div>
      )}

      {/* Loading overlay for email detail */}
      {emailDetailLoading && (
        <div className="loading-overlay">
          <div className="email-loader"></div>
          <p>Loading email...</p>
        </div>
      )}
    </div>
  );
}

export default NERWordCloud;
