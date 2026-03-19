import React, { useState, useEffect, useCallback, useRef } from 'react';
import ChatInput from './components/ChatInput';
import MarketContext from './components/MarketContext';
import RecommendationCard from './components/RecommendationCard';
import EmotionGauge from './components/EmotionGauge';
import JournalList from './components/JournalList';
import StatsPage from './components/StatsPage';
import RulesEditor from './components/RulesEditor';
import SettingsPage from './components/SettingsPage';
import PriceTicker from './components/PriceTicker';
import StreakAlert from './components/StreakAlert';
import { analyzeMessage, healthCheck, overrideEntry } from './api';
import './App.css';

const TABS = [
  { id: 'chat', label: 'Chat', icon: '\u{1F4AC}' },
  { id: 'journal', label: 'Journal', icon: '\u{1F4D3}' },
  { id: 'stats', label: 'Stats', icon: '\u{1F4CA}' },
  { id: 'rules', label: 'Rules', icon: '\u{2699}' },
  { id: 'settings', label: 'Settings', icon: '\u{1F527}' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [health, setHealth] = useState('loading');

  // Chat state - keep history of messages
  const [messages, setMessages] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const [marketContext, setMarketContext] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('ct_market_context')) || {};
    } catch {
      return {};
    }
  });
  const messagesEndRef = useRef(null);

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

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isAnalyzing]);

  const handleSend = useCallback(async (text) => {
    // Add user message to chat
    setMessages((prev) => [...prev, { type: 'user', text, timestamp: new Date() }]);
    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const ctx = {};
      Object.entries(marketContext).forEach(([k, v]) => {
        if (v !== '' && v !== null && v !== undefined) ctx[k] = v;
      });
      const result = await analyzeMessage(text, Object.keys(ctx).length > 0 ? ctx : null);
      // Add bot response to chat
      setMessages((prev) => [...prev, { type: 'bot', result, timestamp: new Date() }]);
    } catch (err) {
      setAnalysisError(err.message || 'Analysis failed');
      setMessages((prev) => [...prev, { type: 'error', text: err.message || 'Analysis failed', timestamp: new Date() }]);
    } finally {
      setIsAnalyzing(false);
    }
  }, [marketContext]);

  const handleOverride = useCallback(async (entryId, action) => {
    try {
      await overrideEntry(entryId, action);
      // Update the message in history
      setMessages((prev) => prev.map((msg) => {
        if (msg.type === 'bot' && msg.result?.entry_id === entryId) {
          return {
            ...msg,
            result: { ...msg.result, manual_override: true, override_action: action },
          };
        }
        return msg;
      }));
    } catch (err) {
      setAnalysisError(err.message || 'Override failed');
    }
  }, []);

  function renderTab() {
    switch (activeTab) {
      case 'chat':
        return (
          <div className="chat-layout">
            <MarketContext values={marketContext} onChange={setMarketContext} />
            <StreakAlert compact={true} />

            {/* Chat messages */}
            <div className="chat-messages">
              {messages.length === 0 && !isAnalyzing && (
                <div className="empty-state">
                  <div className="empty-state-icon-large">
                    <span className="pulse-ring" />
                    <span className="brain-icon">{'\u{1F9E0}'}</span>
                  </div>
                  <div className="empty-state-title">CounterTrade Bot</div>
                  <div className="empty-state-text">
                    Share your trading thoughts and emotions.<br />
                    I'll analyze your sentiment and recommend counter-actions.
                  </div>
                  <div className="empty-state-examples">
                    <button className="example-chip" onClick={() => handleSend("BTC is crashing! I need to sell everything before it goes to zero!")}>
                      "BTC is crashing! Sell everything!"
                    </button>
                    <button className="example-chip" onClick={() => handleSend("Everyone is buying SOL and it keeps pumping. I can't miss this!")}>
                      "SOL keeps pumping, can't miss this"
                    </button>
                    <button className="example-chip" onClick={() => handleSend("I got stopped out again. Going all in with max leverage to win it back.")}>
                      "Stopped out, going all in to recover"
                    </button>
                  </div>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div key={idx} className={`chat-bubble-row ${msg.type}`}>
                  {msg.type === 'user' && (
                    <div className="chat-bubble user-bubble">
                      <div className="bubble-text">{msg.text}</div>
                      <div className="bubble-time">
                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  )}
                  {msg.type === 'bot' && msg.result && (
                    <div className="chat-bubble bot-bubble">
                      <div className="bot-bubble-header">
                        <span className="bot-avatar">{'\u{1F916}'}</span>
                        <span className="bot-name">CounterTrade</span>
                        <span className="bubble-time">
                          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <RecommendationCard
                        result={msg.result}
                        onOverride={(action) => handleOverride(msg.result.entry_id, action)}
                      />
                      <div className="bot-gauges">
                        <EmotionGauge
                          emotion={msg.result.primary_emotion}
                          intensity={msg.result.emotion_intensity}
                          confidence={msg.result.confidence}
                          size={90}
                        />
                        {msg.result.secondary_emotion && (
                          <EmotionGauge
                            emotion={msg.result.secondary_emotion}
                            intensity={Math.round(msg.result.emotion_intensity * 0.6)}
                            confidence={null}
                            size={70}
                          />
                        )}
                      </div>
                    </div>
                  )}
                  {msg.type === 'error' && (
                    <div className="chat-bubble error-bubble">
                      <span className="error-icon">&#9888;</span> {msg.text}
                    </div>
                  )}
                </div>
              ))}

              {isAnalyzing && (
                <div className="chat-bubble-row bot">
                  <div className="chat-bubble bot-bubble typing-bubble">
                    <span className="bot-avatar">{'\u{1F916}'}</span>
                    <div className="typing-indicator">
                      <span /><span /><span />
                    </div>
                    <span className="typing-text">Analyzing your emotions...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

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
          <span className="logo-icon">{'\u{1F504}'}</span>
          <span className="accent">Counter</span>Trade
        </div>
        <nav className="tab-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </nav>
        <span className={`health-dot ${health}`} title={`API: ${health}`} />
      </header>

      <PriceTicker />

      <main className="app-content">
        {renderTab()}
      </main>
    </>
  );
}
