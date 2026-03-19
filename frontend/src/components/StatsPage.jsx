import React, { useState, useEffect } from 'react';
import { getStats, getStreaks } from '../api';
import StreakAlert from './StreakAlert';

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

function MiniStat({ value, label, color }) {
  return (
    <div className="card" style={{ textAlign: 'center' }}>
      <div className="stat-number" style={{ color: color || 'var(--blue)' }}>{value}</div>
      <div className="stat-label">{label}</div>
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

  const emotionCounts = mapToBarData(stats.emotion_counts || {}, 'var(--purple)');
  const stateCounts = mapToBarData(stats.state_counts || {}, 'var(--cyan)');
  const actionCounts = mapToBarData(stats.action_counts || {}, 'var(--blue)');
  const pnlByEmotion = mapToPnlBarData(stats.pnl_by_emotion || {});
  const totalEntries = stats.total_entries ?? 0;
  const reviewedEntries = stats.reviewed_entries ?? 0;
  const avgIntensity = stats.avg_intensity ?? 0;
  const avgConviction = stats.avg_conviction ?? 0;
  const overrideRate = stats.override_rate ?? 0;
  const totalPnl = stats.total_pnl ?? 0;
  const pnlFollowed = stats.pnl_by_followed?.followed ?? null;
  const pnlIgnored = stats.pnl_by_followed?.ignored ?? null;
  const followedCount = stats.pnl_by_followed?.followed_count ?? 0;
  const ignoredCount = stats.pnl_by_followed?.ignored_count ?? 0;

  return (
    <div>
      {/* Streaks & Patterns section */}
      <StatCard title="Emotional Patterns & Streaks">
        <StreakAlert compact={false} />
      </StatCard>

      {/* Summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
        <MiniStat value={totalEntries} label="Total Entries" color="var(--blue)" />
        <MiniStat value={avgIntensity} label="Avg Intensity" color={avgIntensity > 60 ? 'var(--red)' : 'var(--yellow)'} />
        <MiniStat value={avgConviction} label="Avg Conviction" color="var(--green)" />
        <MiniStat value={`${overrideRate}%`} label="Override Rate" color="var(--orange)" />
        <MiniStat
          value={totalPnl >= 0 ? `+${totalPnl.toFixed(0)}` : totalPnl.toFixed(0)}
          label="Total P/L"
          color={totalPnl >= 0 ? 'var(--green)' : 'var(--red)'}
        />
      </div>

      <div className="stats-grid">
        {/* Emotion distribution */}
        <StatCard title="Emotion Distribution">
          <BarChart data={emotionCounts} color="var(--purple)" />
        </StatCard>

        {/* State distribution */}
        <StatCard title="Trading States">
          <BarChart data={stateCounts} color="var(--cyan)" />
        </StatCard>

        {/* Recommended actions */}
        <StatCard title="Actions Recommended">
          <BarChart data={actionCounts} color="var(--blue)" />
        </StatCard>

        {/* P/L by emotion */}
        <StatCard title="P/L by Emotional State">
          <BarChart data={pnlByEmotion} />
        </StatCard>
      </div>

      {/* Following vs Not comparison */}
      {(pnlFollowed != null || pnlIgnored != null) && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <div className="card-header">
            <span className="card-title">P/L: Following Bot vs Not</span>
          </div>
          <div className="comparison-row">
            <div className="comparison-card" style={{ border: '1px solid rgba(16,185,129,0.25)' }}>
              <div className="stat-number" style={{ color: 'var(--green)' }}>
                {pnlFollowed != null ? formatPnlDisplay(pnlFollowed) : '-'}
              </div>
              <div className="stat-label">When Following ({followedCount} trades)</div>
            </div>
            <div className="comparison-card" style={{ border: '1px solid rgba(239,68,68,0.25)' }}>
              <div className="stat-number" style={{ color: 'var(--red)' }}>
                {pnlIgnored != null ? formatPnlDisplay(pnlIgnored) : '-'}
              </div>
              <div className="stat-label">When Ignoring ({ignoredCount} trades)</div>
            </div>
          </div>
        </div>
      )}

      {/* Outcomes breakdown */}
      {stats.outcomes && Object.keys(stats.outcomes).length > 0 && (
        <StatCard title="Outcome Ratings">
          <BarChart
            data={mapToBarData(stats.outcomes, 'var(--yellow)')}
            color="var(--yellow)"
          />
        </StatCard>
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
