import React, { useState, useEffect } from 'react';
import { getStats } from '../api';

function BarChart({ data, color, maxValue }) {
  if (!data || data.length === 0) return <div className="empty-state" style={{ padding: '1rem' }}>No data</div>;
  const max = maxValue || Math.max(...data.map((d) => Math.abs(d.value)), 1);

  return (
    <div className="bar-chart">
      {data.map((item, i) => (
        <div className="bar-row" key={i}>
          <div className="bar-label" title={item.label}>{item.label}</div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: `${(Math.abs(item.value) / max) * 100}%`,
                background: item.color || color || 'var(--blue)',
              }}
            />
          </div>
          <div className="bar-value">{item.display ?? item.value}</div>
        </div>
      ))}
    </div>
  );
}

function StatCard({ title, children }) {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{title}</span>
      </div>
      {children}
    </div>
  );
}

export default function StatsPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getStats();
        if (!cancelled) setStats(data);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load stats');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <div className="loading-text"><span className="spinner" /> Loading stats...</div>;
  }

  if (error) {
    return <div className="error-box">{error}</div>;
  }

  if (!stats) {
    return <div className="empty-state"><div className="empty-state-icon">&#x1f4ca;</div><div className="empty-state-text">No statistics available yet.</div></div>;
  }

  // Parse stats data (adapt to whatever the API returns)
  const emotionCounts = mapToBarData(stats.emotion_counts || stats.emotions || {}, 'var(--purple)');
  const actionCounts = mapToBarData(stats.action_counts || stats.recommendations || {}, 'var(--blue)');
  const actionsTaken = mapToBarData(stats.actions_taken || {}, 'var(--yellow)');
  const pnlByEmotion = mapToPnlBarData(stats.pnl_by_emotion || {});
  const totalEntries = stats.total_entries ?? stats.total ?? 0;
  const reviewedEntries = stats.reviewed_entries ?? stats.reviewed ?? 0;
  const followRate = stats.follow_rate ?? null;
  const pnlFollowing = stats.pnl_following ?? stats.pnl_when_following ?? null;
  const pnlNotFollowing = stats.pnl_not_following ?? stats.pnl_when_not_following ?? null;

  return (
    <div>
      {/* Summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-number" style={{ color: 'var(--blue)' }}>{totalEntries}</div>
          <div className="stat-label">Total Entries</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-number" style={{ color: 'var(--green)' }}>{reviewedEntries}</div>
          <div className="stat-label">Reviewed</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="stat-number" style={{ color: 'var(--yellow)' }}>
            {followRate != null ? `${Math.round(followRate * 100)}%` : '-'}
          </div>
          <div className="stat-label">Follow Rate</div>
        </div>
      </div>

      <div className="stats-grid">
        {/* Emotion distribution */}
        <StatCard title="Most Common Emotional States">
          <BarChart data={emotionCounts} color="var(--purple)" />
        </StatCard>

        {/* Recommended actions */}
        <StatCard title="Actions Recommended">
          <BarChart data={actionCounts} color="var(--blue)" />
        </StatCard>

        {/* Actions actually taken */}
        <StatCard title="Actions Actually Taken">
          <BarChart data={actionsTaken} color="var(--yellow)" />
        </StatCard>

        {/* P/L by emotion */}
        <StatCard title="P/L by Emotional State">
          <BarChart data={pnlByEmotion} />
        </StatCard>
      </div>

      {/* Following vs Not comparison */}
      {(pnlFollowing != null || pnlNotFollowing != null) && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="card-header">
            <span className="card-title">P/L: Following Bot vs Not</span>
          </div>
          <div className="comparison-row">
            <div className="comparison-card" style={{ border: '1px solid var(--green)', borderColor: 'rgba(38,166,65,0.3)' }}>
              <div className="stat-number" style={{ color: 'var(--green)' }}>
                {pnlFollowing != null ? formatPnlDisplay(pnlFollowing) : '-'}
              </div>
              <div className="stat-label">When Following Bot</div>
            </div>
            <div className="comparison-card" style={{ border: '1px solid var(--red)', borderColor: 'rgba(248,81,73,0.3)' }}>
              <div className="stat-number" style={{ color: 'var(--red)' }}>
                {pnlNotFollowing != null ? formatPnlDisplay(pnlNotFollowing) : '-'}
              </div>
              <div className="stat-label">When Not Following</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function mapToBarData(obj, defaultColor) {
  return Object.entries(obj)
    .map(([label, value]) => ({
      label: label.replace(/_/g, ' '),
      value: Number(value) || 0,
      color: defaultColor,
    }))
    .sort((a, b) => b.value - a.value);
}

function mapToPnlBarData(obj) {
  return Object.entries(obj)
    .map(([label, value]) => {
      const num = Number(value) || 0;
      return {
        label: label.replace(/_/g, ' '),
        value: num,
        display: formatPnlDisplay(num),
        color: num >= 0 ? 'var(--green)' : 'var(--red)',
      };
    })
    .sort((a, b) => b.value - a.value);
}

function formatPnlDisplay(val) {
  const num = Number(val);
  if (isNaN(num)) return '-';
  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}`;
}
