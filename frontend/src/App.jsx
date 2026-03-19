import React, { useState, useEffect, useCallback } from 'react';
import ChatInput from './components/ChatInput';
import MarketContext from './components/MarketContext';
import RecommendationCard from './components/RecommendationCard';
import EmotionGauge from './components/EmotionGauge';
import JournalList from './components/JournalList';
import StatsPage from './components/StatsPage';
import RulesEditor from './components/RulesEditor';
import SettingsPage from './components/SettingsPage';
import { analyzeMessage, healthCheck, overrideEntry } from './api';
import './App.css';

const TABS = [
  { id: 'chat', label: 'Chat' },
  { id: 'journal', label: 'Journal' },
  { id: 'stats', label: 'Stats' },
  { id: 'rules', label: 'Rules' },
  { id: 'settings', label: 'Settings' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [health, setHealth] = useState('loading');

  // Chat state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);
  const [marketContext, setMarketContext] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('ct_market_context')) || {};
    } catch {
      return {};
    }
  });

  // Health check on mount and every 30s
  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        await healthCheck();
        if (!cancelled) setHealth('ok');
      } catch {
        if (!cancelled) setHealth('err');
      }
    }
    check();
    const interval = setInterval(check, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  // Persist market context
  useEffect(() => {
    localStorage.setItem('ct_market_context', JSON.stringify(marketContext));
  }, [marketContext]);

  const handleSend = useCallback(async (text) => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const ctx = {};
      Object.entries(marketContext).forEach(([k, v]) => {
        if (v !== '' && v !== null && v !== undefined) ctx[k] = v;
      });
      const result = await analyzeMessage(text, Object.keys(ctx).length > 0 ? ctx : null);
      setAnalysisResult(result);
    } catch (err) {
      setAnalysisError(err.message || 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  }, [marketContext]);

  const handleOverride = useCallback(async (action) => {
    if (!analysisResult?.entry_id) return;
    try {
      await overrideEntry(analysisResult.entry_id, action);
      setAnalysisResult((prev) => ({
        ...prev,
        manual_override: true,
        override_action: action,
      }));
    } catch (err) {
      setAnalysisError(err.message || 'Override failed');
    }
  }, [analysisResult]);

  function renderTab() {
    switch (activeTab) {
      case 'chat':
        return (
          <div className="chat-layout">
            <MarketContext values={marketContext} onChange={setMarketContext} />
            {analysisError && (
              <div className="error-box">{analysisError}</div>
            )}
            {analysisResult && (
              <div className="chat-result-area">
                <RecommendationCard result={analysisResult} onOverride={handleOverride} />
                <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '2rem', flexWrap: 'wrap' }}>
                  <EmotionGauge
                    emotion={analysisResult.primary_emotion}
                    intensity={analysisResult.emotion_intensity}
                    confidence={analysisResult.confidence}
                  />
                  {analysisResult.secondary_emotion && (
                    <EmotionGauge
                      emotion={analysisResult.secondary_emotion}
                      intensity={Math.round(analysisResult.emotion_intensity * 0.6)}
                      confidence={null}
                      size={80}
                    />
                  )}
                </div>
              </div>
            )}
            {!analysisResult && !analysisError && !isAnalyzing && (
              <div className="empty-state">
                <div className="empty-state-icon">&#x1f9e0;</div>
                <div className="empty-state-text">
                  Share your trading thoughts and emotions.<br />
                  CounterTrade will analyze your sentiment and recommend counter-actions.
                </div>
              </div>
            )}
            <ChatInput onSend={handleSend} isLoading={isAnalyzing} />
          </div>
        );
      case 'journal':
        return <JournalList />;
      case 'stats':
        return <StatsPage />;
      case 'rules':
        return <RulesEditor />;
      case 'settings':
        return <SettingsPage />;
      default:
        return null;
    }
  }

  return (
    <>
      <header className="app-header">
        <div className="app-logo">
          <span className="accent">Counter</span>Trade
        </div>
        <nav className="tab-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <span className={`health-dot ${health}`} title={`API: ${health}`} />
      </header>
      <main className="app-content">
        {renderTab()}
      </main>
    </>
  );
}
