import React, { useState } from 'react';

const ACTION_OPTIONS = ['BUY', 'SELL', 'HOLD', 'WAIT', 'NO_TRADE', 'REDUCE'];

function actionClass(action) {
  if (!action) return '';
  const a = action.toLowerCase().replace(/[\s_]+/g, '-');
  if (a.includes('buy')) return 'buy';
  if (a.includes('sell') || a.includes('reduce')) return 'sell';
  if (a.includes('wait') || a.includes('hold')) return 'wait';
  return 'no-trade';
}

function actionBadgeClass(action) {
  const cls = actionClass(action);
  if (cls === 'buy') return 'badge-green';
  if (cls === 'sell') return 'badge-red';
  if (cls === 'wait') return 'badge-yellow';
  return 'badge-muted';
}

function convictionColor(score) {
  if (score >= 70) return 'var(--green)';
  if (score >= 40) return 'var(--yellow)';
  return 'var(--red)';
}

function formatCooldown(minutes) {
  if (!minutes || minutes <= 0) return null;
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins > 0 ? `${mins}m` : ''}`.trim();
}

export default function RecommendationCard({ result, onOverride }) {
  const [overrideAction, setOverrideAction] = useState('');
  const [overriding, setOverriding] = useState(false);

  if (!result) return null;

  const {
    recommended_action,
    conviction,
    primary_emotion,
    secondary_emotion,
    emotion_intensity,
    confidence,
    state_label,
    reasoning,
    distortion_risk,
    disconfirming_evidence,
    guardrails,
    cooldown_minutes,
    manual_override,
    override_action,
  } = result;

  const displayAction = manual_override && override_action ? override_action : recommended_action;

  async function handleOverride() {
    if (!overrideAction) return;
    setOverriding(true);
    try {
      await onOverride(overrideAction);
    } finally {
      setOverriding(false);
      setOverrideAction('');
    }
  }

  return (
    <div className="card">
      {/* Action header */}
      <div className="rec-section">
        <div className={`rec-action ${actionClass(displayAction)}`}>
          {displayAction ? displayAction.replace(/_/g, ' ') : 'UNKNOWN'}
        </div>
        {manual_override && (
          <span className="badge badge-orange" style={{ marginLeft: '0.5rem', fontSize: '0.7rem' }}>
            OVERRIDDEN
          </span>
        )}
        {state_label && (
          <span className={`badge ${actionBadgeClass(recommended_action)}`} style={{ marginTop: '0.25rem' }}>
            {state_label}
          </span>
        )}
      </div>

      {/* Conviction */}
      <div className="rec-section">
        <div className="rec-section-label">Conviction</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="conviction-bar-bg" style={{ flex: 1 }}>
            <div
              className="conviction-bar-fill"
              style={{
                width: `${Math.max(0, Math.min(100, conviction))}%`,
                background: convictionColor(conviction),
              }}
            />
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.9rem',
            fontWeight: 600,
            color: convictionColor(conviction),
            minWidth: '36px',
          }}>
            {conviction}%
          </span>
        </div>
      </div>

      {/* Emotion */}
      <div className="rec-section">
        <div className="rec-section-label">Detected Emotion</div>
        <div className="rec-emotion-row">
          <span className="badge badge-purple">
            {primary_emotion} ({emotion_intensity})
          </span>
          {secondary_emotion && (
            <span className="badge badge-blue">
              {secondary_emotion}
            </span>
          )}
          {confidence != null && (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
              Confidence: {confidence}%
            </span>
          )}
        </div>
      </div>

      {/* Reasoning */}
      {reasoning && (
        <div className="rec-section">
          <div className="rec-section-label">Reasoning</div>
          <p className="rec-reasoning">{reasoning}</p>
        </div>
      )}

      {/* Distortion risk */}
      {distortion_risk && (
        <div className="rec-section">
          <div className="rec-section-label">Distortion Risk</div>
          <p className="rec-reasoning">{distortion_risk}</p>
        </div>
      )}

      {/* Disconfirming evidence */}
      {disconfirming_evidence && (
        <div className="rec-section">
          <div className="rec-section-label">What Would Prove You Right</div>
          <p className="rec-reasoning">{disconfirming_evidence}</p>
        </div>
      )}

      {/* Guardrails */}
      {guardrails && guardrails.length > 0 && (
        <div className="rec-section">
          <div className="rec-section-label">Guardrails</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
            {guardrails.map((g, i) => (
              <span key={i} className="guardrail-badge">
                &#9888; {typeof g === 'string' ? g : JSON.stringify(g)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Cooldown */}
      {cooldown_minutes > 0 && (
        <div className="rec-section">
          <div className="cooldown-banner">
            &#9202; Cooldown: wait {formatCooldown(cooldown_minutes)} before acting
          </div>
        </div>
      )}

      {/* Override */}
      <div className="override-area">
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Override:</span>
        <select
          className="form-select"
          value={overrideAction}
          onChange={(e) => setOverrideAction(e.target.value)}
          style={{ width: 'auto', minWidth: '140px' }}
        >
          <option value="">Choose action...</option>
          {ACTION_OPTIONS.map((a) => (
            <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <button
          className="btn btn-ghost btn-sm"
          onClick={handleOverride}
          disabled={!overrideAction || overriding}
        >
          {overriding ? 'Saving...' : 'Apply Override'}
        </button>
      </div>
    </div>
  );
}
