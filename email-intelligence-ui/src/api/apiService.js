import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Search APIs
export const searchAPI = {
  // Semantic search with optional date filters
  semantic: async (query, limit = 20, dateFrom = null, dateTo = null, sender = null) => {
    const params = { query, limit };
    if (dateFrom) {
      params.date_from = dateFrom;
    }
    if (dateTo) {
      params.date_to = dateTo;
    }
    if (sender) {
      params.sender = sender;
    }
    const response = await api.get('/search/semantic', { params });
    return response.data;
  },
  
  keyword: async (query, page = 1, limit = 20, dateFrom = null, dateTo = null) => {
    const params = { query, page, limit };
    if (dateFrom) {
      params.date_from = dateFrom;
    }
    if (dateTo) {
      params.date_to = dateTo;
    }
    const response = await api.get('/search/keyword', { params });
    return response.data;
  },
};

// Email APIs
export const emailAPI = {
  get: async (emailId) => {
    const response = await api.get(`/emails/${emailId}`);
    return response.data;
  },
  
  list: async (page = 1, limit = 20, filters = {}) => {
    const response = await api.get('/emails', {
      params: { page, limit, ...filters },
    });
    return response.data;
  },
  
  delete: async (emailId) => {
    const response = await api.delete(`/emails/${emailId}`);
    return response.data;
  },
};

// NER APIs
export const nerAPI = {
  getWordcloud: async (entityTypes = null, limit = 100, minCount = 1) => {
    const params = { limit, min_count: minCount };
    if (entityTypes) {
      params.entity_types = entityTypes;
    }
    const response = await api.get('/ner/wordcloud', { params });
    return response.data;
  },
  
  getBreakdown: async () => {
    const response = await api.get('/ner/breakdown');
    return response.data;
  },
  
  getTopEntities: async (entityTypes = null, limit = 50) => {
    const params = { limit };
    if (entityTypes) {
      params.entity_types = entityTypes;
    }
    const response = await api.get('/ner/top-entities', { params });
    return response.data;
  },
  
  // Get emails containing a specific entity (for clickable word cloud)
  getEmailsByEntity: async (entityText, entityType = null, page = 1, limit = 20) => {
    const params = { entity_text: entityText, page, limit };
    if (entityType) {
      params.entity_type = entityType;
    }
    const response = await api.get('/ner/emails-by-entity', { params });
    return response.data;
  },
  
  // Get phrases word cloud (noun phrases, verb phrases, actions)
  getPhrasesWordcloud: async (phraseType = 'all', limit = 100) => {
    const params = { phrase_type: phraseType, limit };
    const response = await api.get('/ner/phrases/wordcloud', { params });
    return response.data;
  },
  
  // Extract phrases from text
  extractPhrases: async (text) => {
    const response = await api.post('/ner/extract-phrases', null, {
      params: { text }
    });
    return response.data;
  },
  
  // Get phrases from specific email
  getEmailPhrases: async (emailId) => {
    const response = await api.get(`/ner/email/${emailId}/phrases`);
    return response.data;
  },
  
  // Get emails containing a specific phrase (for clickable phrase word cloud)
  getEmailsByPhrase: async (phraseText, phraseType = null, page = 1, limit = 20) => {
    const params = { phrase_text: phraseText, page, limit };
    if (phraseType) {
      params.phrase_type = phraseType;
    }
    const response = await api.get('/ner/emails-by-phrase', { params });
    return response.data;
  },
};

// Volume Alerts APIs (with subscriber email support)
export const alertsAPI = {
  // Get form options for dropdowns
  getOptions: async () => {
    const response = await api.get('/volume-alerts/options');
    return response.data;
  },
  
  // Get entity values for dropdown
  getEntityValues: async (entityType = null, limit = 100) => {
    const params = { limit };
    if (entityType) {
      params.entity_type = entityType;
    }
    const response = await api.get('/volume-alerts/entity-values', { params });
    return response.data;
  },
  
  // Get alert statistics
  getStats: async () => {
    const alerts = await alertsAPI.list();
    const triggered = await alertsAPI.getTriggeredAlerts(100);
    
    const enabledAlerts = alerts.alerts.filter(a => a.enabled).length;
    const triggeredLast24h = triggered.triggered.filter(t => {
      const triggeredAt = new Date(t.triggered_at);
      const now = new Date();
      return (now - triggeredAt) < 24 * 60 * 60 * 1000;
    }).length;
    
    const bySeverity = { low: 0, medium: 0, high: 0, critical: 0 };
    alerts.alerts.forEach(a => {
      bySeverity[a.severity] = (bySeverity[a.severity] || 0) + 1;
    });
    
    return {
      total_alerts: alerts.total,
      enabled_alerts: enabledAlerts,
      triggered_last_24h: triggeredLast24h,
      by_severity: bySeverity,
    };
  },
  
  // List all alerts
  list: async (enabledOnly = false, alertType = null, limit = 100) => {
    const params = { enabled_only: enabledOnly, limit };
    if (alertType) {
      params.alert_type = alertType;
    }
    const response = await api.get('/volume-alerts', { params });
    return response.data;
  },
  
  // Create new alert
  create: async (alertData) => {
    const response = await api.post('/volume-alerts', alertData);
    return response.data;
  },
  
  // Get single alert
  get: async (alertId) => {
    const response = await api.get(`/volume-alerts/${alertId}`);
    return response.data;
  },
  
  // Update alert
  update: async (alertId, alertData) => {
    const response = await api.put(`/volume-alerts/${alertId}`, alertData);
    return response.data;
  },
  
  // Delete alert
  delete: async (alertId) => {
    const response = await api.delete(`/volume-alerts/${alertId}`);
    return response.data;
  },
  
  // Toggle alert enabled/disabled (manual implementation)
  toggle: async (alertId) => {
    const alert = await alertsAPI.get(alertId);
    const response = await api.put(`/volume-alerts/${alertId}`, {
      enabled: !alert.enabled,
    });
    return response.data;
  },
  
  // Evaluate single alert
  evaluate: async (alertId) => {
    const response = await api.post(`/volume-alerts/${alertId}/evaluate`);
    return response.data;
  },
  
  // Evaluate all alerts
  evaluateAll: async () => {
    const response = await api.post('/volume-alerts/evaluate-all');
    return response.data;
  },
  
  // Get all triggered alerts
  getTriggeredAlerts: async (limit = 100) => {
    const response = await api.get('/volume-alerts/triggered/all', {
      params: { limit },
    });
    return response.data;
  },
};

// ============ Unified Alerts APIs ============

export const unifiedAlertsAPI = {
  // Get form options for all dropdowns
  getOptions: async () => {
    const response = await api.get('/unified-alerts/options');
    return response.data;
  },
  
  // Get dashboard stats
  getStats: async () => {
    const response = await api.get('/unified-alerts/stats');
    return response.data;
  },
  
  // Get entity values for dropdown
  getEntityValues: async (entityType = null, limit = 100) => {
    const params = { limit };
    if (entityType) {
      params.entity_type = entityType;
    }
    const response = await api.get('/unified-alerts/entity-values', { params });
    return response.data;
  },
  
  // ============ Data Quality Alerts ============
  
  dataQuality: {
    list: async (enabledOnly = false, limit = 100) => {
      const response = await api.get('/unified-alerts/data-quality', {
        params: { enabled_only: enabledOnly, limit }
      });
      return response.data;
    },
    
    create: async (data) => {
      const response = await api.post('/unified-alerts/data-quality', data);
      return response.data;
    },
    
    get: async (id) => {
      const response = await api.get(`/unified-alerts/data-quality/${id}`);
      return response.data;
    },
    
    update: async (id, data) => {
      const response = await api.put(`/unified-alerts/data-quality/${id}`, data);
      return response.data;
    },
    
    delete: async (id) => {
      const response = await api.delete(`/unified-alerts/data-quality/${id}`);
      return response.data;
    },
    
    toggle: async (id) => {
      const response = await api.patch(`/unified-alerts/data-quality/${id}/toggle`);
      return response.data;
    },
    
    evaluate: async (id) => {
      const response = await api.post(`/unified-alerts/data-quality/${id}/evaluate`);
      return response.data;
    },
  },
  
  // ============ Entity Type Alerts ============
  
  entityType: {
    list: async (enabledOnly = false, limit = 100) => {
      const response = await api.get('/unified-alerts/entity-type', {
        params: { enabled_only: enabledOnly, limit }
      });
      return response.data;
    },
    
    create: async (data) => {
      const response = await api.post('/unified-alerts/entity-type', data);
      return response.data;
    },
    
    get: async (id) => {
      const response = await api.get(`/unified-alerts/entity-type/${id}`);
      return response.data;
    },
    
    update: async (id, data) => {
      const response = await api.put(`/unified-alerts/entity-type/${id}`, data);
      return response.data;
    },
    
    delete: async (id) => {
      const response = await api.delete(`/unified-alerts/entity-type/${id}`);
      return response.data;
    },
    
    toggle: async (id) => {
      const response = await api.patch(`/unified-alerts/entity-type/${id}/toggle`);
      return response.data;
    },
    
    evaluate: async (id) => {
      const response = await api.post(`/unified-alerts/entity-type/${id}/evaluate`);
      return response.data;
    },
  },
  
  // ============ Smart AI Alerts ============
  
  smartAI: {
    list: async (enabledOnly = false, limit = 100) => {
      const response = await api.get('/unified-alerts/smart-ai', {
        params: { enabled_only: enabledOnly, limit }
      });
      return response.data;
    },
    
    create: async (data) => {
      const response = await api.post('/unified-alerts/smart-ai', data);
      return response.data;
    },
    
    get: async (id) => {
      const response = await api.get(`/unified-alerts/smart-ai/${id}`);
      return response.data;
    },
    
    update: async (id, data) => {
      const response = await api.put(`/unified-alerts/smart-ai/${id}`, data);
      return response.data;
    },
    
    delete: async (id) => {
      const response = await api.delete(`/unified-alerts/smart-ai/${id}`);
      return response.data;
    },
    
    toggle: async (id) => {
      const response = await api.patch(`/unified-alerts/smart-ai/${id}/toggle`);
      return response.data;
    },
    
    evaluate: async (id) => {
      const response = await api.post(`/unified-alerts/smart-ai/${id}/evaluate`);
      return response.data;
    },
  },
  
  // ============ Dashboard APIs ============
  
  dashboard: {
    getDateRange: async () => {
      const response = await api.get('/unified-alerts/dashboard/date-range');
      return response.data;
    },
    
    getActivity: async (params = {}) => {
      const defaults = {
        hours_back: 720,
        algorithm: 'dbscan',
        dbscan_eps: 0.5,
        dbscan_min_samples: 3,
        kmeans_clusters: 3,
        use_all_data: true, // Default to using all available data
      };
      
      // Build query params, excluding undefined/null values
      const queryParams = { ...defaults };
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
          queryParams[key] = params[key];
        }
      });
      
      const response = await api.get('/unified-alerts/dashboard/activity', {
        params: queryParams
      });
      return response.data;
    },
    
    getDataPointEmails: async (timestamp, aggregation = 'hourly', limit = 50, entityType = null, entityValue = null, searchQuery = null, similarityThreshold = 0.5) => {
      const params = { timestamp, aggregation, limit };
      if (entityType && entityType !== 'ALL') {
        params.entity_type = entityType;
      }
      if (entityValue) {
        params.entity_value = entityValue;
      }
      // For Smart AI alerts - use semantic search
      if (searchQuery) {
        params.search_query = searchQuery;
        params.similarity_threshold = similarityThreshold;
      }
      const response = await api.get('/unified-alerts/dashboard/data-point-emails', { params });
      return response.data;
    },
    
    getRecentAlerts: async (limit = 50) => {
      const response = await api.get('/unified-alerts/dashboard/recent-alerts', {
        params: { limit }
      });
      return response.data;
    },
  },
  
  // Evaluate all alerts
  evaluateAll: async () => {
    const response = await api.post('/unified-alerts/evaluate-all');
    return response.data;
  },
};

export default api;
