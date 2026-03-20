import React, { useState } from 'react';

const ACTION_OPTIONS = ['BUY', 'SELL', 'HOLD', 'WAIT', 'NO_TRADE', 'REDUCE'];

function actionClass(action) {
  if (!action) return '';
  const a = action.toLowerCase().replace(/[\s_]+/g, '-');
  if (a.includes('buy')) return 'buy';
  if (a.includes('sell')) return 'sell';
  if (a.includes('reduce')) return 'reduce';
  if (a.includes('wait') || a.includes('hold')) return 'wait';
  return 'no-trade';
}

function actionBadgeClass(action) {
  const cls = actionClass(action);
  if (cls === 'buy') return 'badge-green';
  if (cls === 'sell' || cls === 'reduce') return 'badge-red';
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
    cooldown_warning,
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
    <div>
      {/* Action header */}
      <div className="rec-section">
        <div className={`rec-action ${actionClass(displayAction)}`}>
          {displayAction ? displayAction.replace(/_/g, ' ') : 'UNKNOWN'}
          {manual_override && (
            <span className="badge badge-orange" style={{ marginLeft: '0.5rem', fontSize: '0.65rem', verticalAlign: 'middle' }}>
              OVERRIDDEN
            </span>
          )}
        </div>
        <div className="rec-emotion-row" style={{ marginTop: '0.25rem' }}>
          {state_label && (
            <span className={`badge ${actionBadgeClass(recommended_action)}`}>
              {state_label}
            </span>
          )}
          <span className="badge badge-purple">
            {primary_emotion} ({emotion_intensity})
          </span>
          {secondary_emotion && (
            <span className="badge badge-blue">
              {secondary_emotion}
            </span>
          )}
        </div>
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
                background: `linear-gradient(90deg, ${convictionColor(conviction)}, ${convictionColor(conviction)}88)`,
              }}
            />
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
            fontWeight: 700,
            color: convictionColor(conviction),
            minWidth: '36px',
          }}>
            {conviction}%
          </span>
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
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
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

      {/* Cooldown warning from previous analysis */}
      {cooldown_warning && (
        <div className="rec-section">
          <div className="cooldown-warning-banner">
            &#9888; {cooldown_warning}
          </div>
        </div>
      )}

      {/* Override */}
      <div className="override-area">
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Override:</span>
        <select
          className="form-select"
          value={overrideAction}
          onChange={(e) => setOverrideAction(e.target.value)}
          style={{ width: 'auto', minWidth: '120px', fontSize: '0.82rem', padding: '0.3rem 0.5rem' }}
        >
          <option value="">Choose...</option>
          {ACTION_OPTIONS.map((a) => (
            <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <button
          className="btn btn-ghost btn-sm"
          onClick={handleOverride}
          disabled={!overrideAction || overriding}
        >
          {overriding ? 'Saving...' : 'Apply'}
        </button>
      </div>
    </div>
  );
}
