import React, { useState } from 'react';
import { reviewEntry } from '../api';

const FOLLOW_OPTIONS = [
  { value: 'followed', label: 'Followed bot recommendation' },
  { value: 'did_opposite', label: 'Did the opposite' },
  { value: 'partial_follow', label: 'Partially followed' },
  { value: 'ignored', label: 'Ignored / did nothing' },
];

const OUTCOME_OPTIONS = [
  { value: 'bot_right', label: 'Bot was right' },
  { value: 'bot_wrong', label: 'Bot was wrong' },
  { value: 'emotion_wrong', label: 'Emotion classification was wrong' },
  { value: 'too_aggressive', label: 'Recommendation too aggressive' },
  { value: 'too_passive', label: 'Recommendation too passive' },
];

export default function ReviewModal({ entry, onClose, onSaved }) {
  const [userAction, setUserAction] = useState(entry?.user_action_taken || '');
  const [outcomeRating, setOutcomeRating] = useState(entry?.outcome_rating || '');
  const [pnl, setPnl] = useState(entry?.pnl_after_trade ?? '');
  const [notes, setNotes] = useState(entry?.notes_after_trade || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  if (!entry) return null;

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const data = {};
      if (userAction) data.user_action_taken = userAction;
      if (outcomeRating) data.outcome_rating = outcomeRating;
      if (pnl !== '' && pnl !== null) data.pnl_after_trade = Number(pnl);
      if (notes) data.notes_after_trade = notes;
      await reviewEntry(entry.id, data);
      onSaved();
    } catch (err) {
      setError(err.message || 'Failed to save review');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-title">Review Entry</div>

        {/* Summary of original */}
        <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', fontSize: '0.85rem' }}>
          <div style={{ color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
            {new Date(entry.timestamp).toLocaleString()}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: '0.5rem' }}>
            &ldquo;{entry.raw_text?.substring(0, 200)}{entry.raw_text?.length > 200 ? '...' : ''}&rdquo;
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span className="badge badge-purple">{entry.primary_emotion}</span>
            <span className="badge badge-blue">{entry.state_label}</span>
            <span className="badge badge-yellow">{entry.recommended_action?.replace(/_/g, ' ')}</span>
          </div>
        </div>

        {error && <div className="error-box">{error}</div>}

        <div className="form-group">
          <label className="form-label">What did you actually do?</label>
          <select
            className="form-select"
            value={userAction}
            onChange={(e) => setUserAction(e.target.value)}
          >
            <option value="">Select...</option>
            {FOLLOW_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Outcome Rating</label>
          <select
            className="form-select"
            value={outcomeRating}
            onChange={(e) => setOutcomeRating(e.target.value)}
          >
            <option value="">Select...</option>
            {OUTCOME_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">P/L After Trade</label>
          <input
            className="form-input"
            type="number"
            step="any"
            placeholder="e.g. 150 or -50"
            value={pnl}
            onChange={(e) => setPnl(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Notes</label>
          <textarea
            className="form-textarea"
            rows={3}
            placeholder="What did you learn? Would you do it differently?"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Review'}
          </button>
        </div>
      </div>
    </div>
  );
}
