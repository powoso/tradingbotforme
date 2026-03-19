import React, { useState, useEffect } from 'react';
import { getStreaks } from '../api';

const SEVERITY_COLORS = {
  high: 'var(--red)',
  medium: 'var(--orange)',
  low: 'var(--yellow)',
};

const TREND_ICONS = {
  worsening: { icon: '\u2191', color: 'var(--red)', label: 'Worsening' },
  improving: { icon: '\u2193', color: 'var(--green)', label: 'Improving' },
  stable: { icon: '\u2192', color: 'var(--text-muted)', label: 'Stable' },
  rising: { icon: '\u2191', color: 'var(--red)', label: 'Rising' },
  falling: { icon: '\u2193', color: 'var(--green)', label: 'Falling' },
  neutral: { icon: '\u2014', color: 'var(--text-muted)', label: 'Neutral' },
};

export default function StreakAlert({ compact = false }) {
  const [streakData, setStreakData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getStreaks();
        if (!cancelled) setStreakData(data);
      } catch {
        // Silently fail
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading || !streakData) return null;

  const { current_streak, patterns, warnings, emotional_trend, intensity_trend, recent_emotions } = streakData;

  // Don't show if nothing interesting
  const hasContent = (current_streak && current_streak.is_dangerous) ||
    patterns.length > 0 ||
    warnings.length > 0;

  if (!hasContent && compact) return null;

  if (compact) {
    // Show a small alert banner
    return (
      <div className="streak-alert-compact">
        {warnings.length > 0 && (
          <div className="streak-warning-banner">
            <span className="streak-warning-icon">&#9888;</span>
            <span>{warnings[0]}</span>
          </div>
        )}
        {!warnings.length && current_streak && current_streak.is_dangerous && (
          <div className="streak-warning-banner">
            <span className="streak-warning-icon">&#x1f525;</span>
            <span>
              {current_streak.count}x {current_streak.emotion} streak
              (avg intensity: {current_streak.avg_intensity})
            </span>
          </div>
        )}
      </div>
    );
  }

  const emotionTrend = TREND_ICONS[emotional_trend] || TREND_ICONS.neutral;
  const intTrend = TREND_ICONS[intensity_trend] || TREND_ICONS.stable;

  return (
    <div className="streak-section">
      {/* Trend indicators */}
      <div className="streak-trends">
        <div className="streak-trend-item">
          <span className="streak-trend-label">Emotional Trend</span>
          <span className="streak-trend-value" style={{ color: emotionTrend.color }}>
            {emotionTrend.icon} {emotionTrend.label}
          </span>
        </div>
        <div className="streak-trend-item">
          <span className="streak-trend-label">Intensity</span>
          <span className="streak-trend-value" style={{ color: intTrend.color }}>
            {intTrend.icon} {intTrend.label}
          </span>
        </div>
        {current_streak && (
          <div className="streak-trend-item">
            <span className="streak-trend-label">Current Streak</span>
            <span className="streak-trend-value" style={{
              color: current_streak.is_dangerous ? 'var(--red)' : 'var(--text-primary)'
            }}>
              {current_streak.count}x {current_streak.emotion}
            </span>
          </div>
        )}
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="streak-warnings">
          {warnings.map((w, i) => (
            <div key={i} className="streak-warning-banner">
              <span className="streak-warning-icon">&#9888;</span>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Patterns */}
      {patterns.length > 0 && (
        <div className="streak-patterns">
          {patterns.map((p, i) => (
            <div key={i} className="streak-pattern-card" style={{
              borderLeftColor: SEVERITY_COLORS[p.severity] || 'var(--yellow)'
            }}>
              <div className="streak-pattern-label">{p.label}</div>
              <div className="streak-pattern-desc">{p.description}</div>
            </div>
          ))}
        </div>
      )}

      {/* Recent emotion timeline */}
      {recent_emotions && recent_emotions.length > 0 && (
        <div className="streak-timeline">
          <div className="streak-timeline-label">Recent Emotions</div>
          <div className="streak-timeline-items">
            {recent_emotions.slice(0, 8).map((e, i) => (
              <div
                key={i}
                className="streak-timeline-dot"
                title={`${e.emotion} (${e.intensity}) - ${e.state}`}
                style={{
                  background: getEmotionColor(e.emotion),
                  opacity: 1 - (i * 0.08),
                  width: `${Math.max(12, e.intensity / 4)}px`,
                  height: `${Math.max(12, e.intensity / 4)}px`,
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function getEmotionColor(emotion) {
  const map = {
    anger: 'var(--red)',
    revenge: 'var(--red)',
    panic: 'var(--red)',
    despair: 'var(--red)',
    fear: 'var(--orange)',
    capitulation: 'var(--orange)',
    fomo: 'var(--yellow)',
    greed: 'var(--yellow)',
    euphoria: 'var(--purple)',
    overconfidence: 'var(--purple)',
    exhaustion: 'var(--blue)',
    calm: 'var(--green)',
  };
  return map[emotion] || 'var(--text-muted)';
}
