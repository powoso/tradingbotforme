import React, { useState, useEffect } from 'react';
import { getPortfolio } from '../api';

function emotionBadgeClass(emotion) {
  if (!emotion) return 'badge-muted';
  const e = emotion.toLowerCase();
  if (['fear', 'panic', 'despair'].includes(e)) return 'badge-red';
  if (['greed', 'fomo', 'euphoria', 'overconfidence'].includes(e)) return 'badge-orange';
  if (['calm'].includes(e)) return 'badge-green';
  if (['anger', 'revenge'].includes(e)) return 'badge-red';
  return 'badge-purple';
}

function actionBadgeClass(action) {
  if (!action) return 'badge-muted';
  const a = action.toLowerCase();
  if (a.includes('buy')) return 'badge-green';
  if (a.includes('sell') || a.includes('reduce')) return 'badge-red';
  if (a.includes('wait') || a.includes('hold')) return 'badge-yellow';
  return 'badge-muted';
}

export default function PortfolioSummary() {
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getPortfolio();
        if (!cancelled) setPortfolio(Array.isArray(data) ? data : []);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load portfolio');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <div className="loading-text"><span className="spinner" /> Loading portfolio...</div>;
  }

  if (error) {
    return <div className="error-box">{error}</div>;
  }

  if (portfolio.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">{'\u{1F4BC}'}</div>
        <div className="empty-state-text">
          No asset data yet. Include an asset name in your market context when analyzing trades.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <span className="card-title">Portfolio Overview</span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {portfolio.length} asset{portfolio.length !== 1 ? 's' : ''} tracked
          </span>
        </div>

        <div className="portfolio-grid">
          {portfolio.map((item) => {
            const topEmotion = Object.entries(item.emotions)
              .sort((a, b) => b[1] - a[1])[0];
            const topAction = Object.entries(item.actions)
              .sort((a, b) => b[1] - a[1])[0];

            return (
              <div key={item.asset} className="portfolio-card">
                <div className="portfolio-card-header">
                  <span className="portfolio-asset">{item.asset}</span>
                  <span
                    className="portfolio-pnl"
                    style={{ color: item.total_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}
                  >
                    {item.total_pnl >= 0 ? '+' : ''}{item.total_pnl.toFixed(2)}
                  </span>
                </div>

                <div className="portfolio-stats-row">
                  <div className="portfolio-stat">
                    <span className="portfolio-stat-value">{item.total_entries}</span>
                    <span className="portfolio-stat-label">Entries</span>
                  </div>
                  <div className="portfolio-stat">
                    <span className={`badge ${emotionBadgeClass(item.last_emotion)}`}>
                      {item.last_emotion}
                    </span>
                    <span className="portfolio-stat-label">Last Emotion</span>
                  </div>
                  <div className="portfolio-stat">
                    <span className={`badge ${actionBadgeClass(item.last_action)}`}>
                      {item.last_action?.replace(/_/g, ' ')}
                    </span>
                    <span className="portfolio-stat-label">Last Rec.</span>
                  </div>
                </div>

                {/* Emotion breakdown mini bar */}
                <div className="portfolio-breakdown">
                  <div className="portfolio-breakdown-label">Emotion History</div>
                  <div className="portfolio-breakdown-bar">
                    {Object.entries(item.emotions)
                      .sort((a, b) => b[1] - a[1])
                      .map(([emotion, count]) => {
                        const pct = (count / item.total_entries) * 100;
                        const colors = {
                          fear: 'var(--red)', panic: 'var(--red)', despair: 'var(--red)',
                          anger: '#dc2626', revenge: '#dc2626',
                          greed: 'var(--orange)', fomo: 'var(--orange)',
                          euphoria: 'var(--yellow)', overconfidence: 'var(--yellow)',
                          calm: 'var(--green)', exhaustion: 'var(--purple)',
                        };
                        return (
                          <div
                            key={emotion}
                            className="portfolio-breakdown-segment"
                            style={{
                              width: `${Math.max(pct, 3)}%`,
                              background: colors[emotion] || 'var(--blue)',
                            }}
                            title={`${emotion}: ${count}`}
                          />
                        );
                      })}
                  </div>
                </div>

                <div className="portfolio-last-time">
                  Last: {new Date(item.last_timestamp).toLocaleDateString()} {new Date(item.last_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
