import { useState, useEffect } from 'react';
import Search from './components/Search';
import NERWordCloud from './components/NERWordCloud';
import SmartAlerts from './components/SmartAlerts';
import AlertsDashboard from './components/AlertsDashboard';
import './App.css';

const TABS = [
  { id: 'search', label: 'Search', icon: 'search' },
  { id: 'ner', label: 'NER', icon: 'cloud' },
  { id: 'alerts', label: 'Alerts', icon: 'bell' },
  { id: 'dashboard', label: 'Alerts Dashboard', icon: 'chart' },
];

function App() {
  // Read tab from URL query parameter
  const getInitialTab = () => {
    const params = new URLSearchParams(window.location.search);
    const tabParam = params.get('tab');
    if (tabParam && TABS.some(t => t.id === tabParam)) {
      return tabParam;
    }
    return 'search';
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);

  // Update URL when tab changes
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    const url = new URL(window.location.href);
    url.searchParams.set('tab', tabId);
    window.history.pushState({}, '', url);
  };

  // Listen for browser back/forward
  useEffect(() => {
    const handlePopState = () => {
      setActiveTab(getInitialTab());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const renderIcon = (icon) => {
    switch (icon) {
      case 'search':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
        );
      case 'cloud':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
          </svg>
        );
      case 'bell':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        );
      case 'chart':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 3v18h18" />
            <path d="m19 9-5 5-4-4-3 3" />
          </svg>
        );
      default:
        return null;
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'search':
        return <Search />;
      case 'ner':
        return <NERWordCloud />;
      case 'alerts':
        return <SmartAlerts />;
      case 'dashboard':
        return <AlertsDashboard />;
      default:
        return <Search />;
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
              <polyline points="22,6 12,13 2,6" />
            </svg>
          </div>
          <div className="brand-text">
            <h1>Email Intelligence</h1>
            <span>AI-Powered Analysis</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="main-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => handleTabChange(tab.id)}
            >
              <span className="nav-icon">{renderIcon(tab.icon)}</span>
              <span className="nav-label">{tab.label}</span>
              {activeTab === tab.id && <span className="nav-indicator" />}
            </button>
          ))}
        </nav>

        <div className="header-actions">
          <button className="status-indicator">
            <span className="status-dot"></span>
            API Connected
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {renderContent()}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <span>Email Intelligence API v1.0</span>
        <span className="separator">•</span>
        <span>NER-Powered Analysis</span>
      </footer>
    </div>
  );
}

export default App;
