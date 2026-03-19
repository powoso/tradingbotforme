import React from 'react';

function actionBadgeClass(action) {
  if (!action) return 'badge-muted';
  const a = action.toLowerCase();
  if (a.includes('buy')) return 'badge-green';
  if (a.includes('sell') || a.includes('reduce')) return 'badge-red';
  if (a.includes('wait') || a.includes('hold')) return 'badge-yellow';
  return 'badge-muted';
}

function emotionBadgeClass(emotion) {
  if (!emotion) return 'badge-muted';
  const e = emotion.toLowerCase();
  if (['fear', 'panic', 'despair', 'anger', 'revenge'].includes(e)) return 'badge-red';
  if (['greed', 'fomo', 'euphoria', 'overconfidence'].includes(e)) return 'badge-orange';
  if (e === 'calm') return 'badge-green';
  return 'badge-purple';
}

function formatPnl(val) {
  if (val == null || val === '') return '-';
  const num = Number(val);
  const sign = num >= 0 ? '+' : '';
  return (
    <span style={{ color: num >= 0 ? 'var(--green)' : 'var(--red)', fontFamily: 'var(--font-mono)' }}>
      {sign}{num.toFixed(2)}
    </span>
  );
}

function parseJson(str) {
  if (!str) return null;
  if (typeof str === 'object') return str;
  try { return JSON.parse(str); } catch { return null; }
}

export default function JournalEntry({ entry, onReview }) {
  if (!entry) return null;

  const marketCtx = parseJson(entry.market_context_json);
  const guardrails = parseJson(entry.guardrails) || [];

  return (
    <div style={{ padding: '1rem' }}>
      {/* Original message */}
      <div className="rec-section">
        <div className="rec-section-label">Original Message</div>
        <p className="rec-reasoning" style={{ fontStyle: 'italic' }}>
          &ldquo;{entry.raw_text}&rdquo;
        </p>
      </div>

      {/* Meta row */}
      <div className="rec-section">
        <div className="rec-meta">
          <span className={`badge ${emotionBadgeClass(entry.primary_emotion)}`}>
            {entry.primary_emotion} ({entry.emotion_intensity})
          </span>
          {entry.secondary_emotion && (
            <span className={`badge ${emotionBadgeClass(entry.secondary_emotion)}`}>
              {entry.secondary_emotion}
            </span>
          )}
          <span className={`badge ${actionBadgeClass(entry.recommended_action)}`}>
            {entry.recommended_action?.replace(/_/g, ' ')}
          </span>
          {entry.state_label && (
            <span className="badge badge-blue">{entry.state_label}</span>
          )}
          {entry.conviction != null && (
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Conviction: {entry.conviction}%
            </span>
          )}
        </div>
      </div>

      {/* Reasoning */}
      {entry.reasoning && (
        <div className="rec-section">
          <div className="rec-section-label">Reasoning</div>
          <p className="rec-reasoning">{entry.reasoning}</p>
        </div>
      )}

      {/* Guardrails */}
      {guardrails.length > 0 && (
        <div className="rec-section">
          <div className="rec-section-label">Guardrails</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
            {guardrails.map((g, i) => (
              <span key={i} className="guardrail-badge">&#9888; {g}</span>
            ))}
          </div>
        </div>
      )}

      {/* Market context if present */}
      {marketCtx && Object.keys(marketCtx).length > 0 && (
        <div className="rec-section">
          <div className="rec-section-label">Market Context</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {marketCtx.asset && <span><strong>Asset:</strong> {marketCtx.asset}</span>}
            {marketCtx.current_price != null && <span><strong>Price:</strong> {marketCtx.current_price}</span>}
            {marketCtx.recent_move_pct != null && <span><strong>Move:</strong> {marketCtx.recent_move_pct}%</span>}
            {marketCtx.time_horizon && <span><strong>Horizon:</strong> {marketCtx.time_horizon}</span>}
            {marketCtx.position_size != null && <span><strong>Size:</strong> {marketCtx.position_size}</span>}
            {marketCtx.thesis && <span><strong>Thesis:</strong> {marketCtx.thesis}</span>}
          </div>
        </div>
      )}

      {/* Review info */}
      {(entry.user_action_taken || entry.outcome_rating || entry.notes_after_trade) && (
        <div className="rec-section">
          <div className="rec-section-label">Review</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {entry.user_action_taken && <div><strong>Action taken:</strong> {entry.user_action_taken}</div>}
            {entry.outcome_rating && <div><strong>Rating:</strong> {entry.outcome_rating.replace(/_/g, ' ')}</div>}
            {entry.notes_after_trade && <div><strong>Notes:</strong> {entry.notes_after_trade}</div>}
          </div>
        </div>
      )}

      {/* P/L and actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-secondary)' }}>
        <div>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginRight: '0.5rem' }}>P/L:</span>
          {formatPnl(entry.pnl_after_trade)}
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => onReview(entry)}>
          {entry.outcome_rating ? 'Edit Review' : 'Review'}
        </button>
      </div>
    </div>
  );
}
