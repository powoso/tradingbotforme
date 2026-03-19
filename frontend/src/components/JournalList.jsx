import React, { useState, useEffect, useCallback } from 'react';
import { getJournal } from '../api';
import JournalEntry from './JournalEntry';
import ReviewModal from './ReviewModal';

const EMOTION_OPTIONS = ['', 'anger', 'despair', 'capitulation', 'revenge', 'fomo', 'panic', 'greed', 'euphoria', 'exhaustion', 'overconfidence', 'fear', 'calm'];
const STATE_OPTIONS = ['', 'capitulation', 'panic-selling', 'revenge-trading', 'FOMO-chasing', 'greed-top', 'tilted', 'calm', 'disciplined', 'uncertain'];
const ACTION_OPTIONS = ['', 'BUY', 'SELL', 'HOLD', 'WAIT', 'NO_TRADE', 'REDUCE'];

export default function JournalList() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [reviewEntry, setReviewEntry] = useState(null);

  // Filters
  const [emotionFilter, setEmotionFilter] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const filters = {};
      if (emotionFilter) filters.emotion = emotionFilter;
      if (stateFilter) filters.state = stateFilter;
      if (actionFilter) filters.action = actionFilter;
      if (dateFrom) filters.date_from = dateFrom;
      if (dateTo) filters.date_to = dateTo;
      const data = await getJournal(filters);
      setEntries(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Failed to load journal');
    } finally {
      setLoading(false);
    }
  }, [emotionFilter, stateFilter, actionFilter, dateFrom, dateTo]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  function toggleExpand(id) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  function handleReviewSaved() {
    setReviewEntry(null);
    fetchEntries();
  }

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
    if (['fear', 'panic', 'despair'].includes(e)) return 'badge-red';
    if (['greed', 'fomo', 'euphoria', 'overconfidence'].includes(e)) return 'badge-orange';
    if (['calm'].includes(e)) return 'badge-green';
    if (['anger', 'revenge'].includes(e)) return 'badge-red';
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

  return (
    <div>
      {/* Filter bar */}
      <div className="filter-bar">
        <select className="form-select" value={emotionFilter} onChange={(e) => setEmotionFilter(e.target.value)}>
          <option value="">All Emotions</option>
          {EMOTION_OPTIONS.filter(Boolean).map((em) => (
            <option key={em} value={em}>{em.charAt(0).toUpperCase() + em.slice(1)}</option>
          ))}
        </select>
        <select className="form-select" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
          <option value="">All States</option>
          {STATE_OPTIONS.filter(Boolean).map((st) => (
            <option key={st} value={st}>{st}</option>
          ))}
        </select>
        <select className="form-select" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
          <option value="">All Actions</option>
          {ACTION_OPTIONS.filter(Boolean).map((ac) => (
            <option key={ac} value={ac}>{ac.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <input
          className="form-input"
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          title="From date"
        />
        <input
          className="form-input"
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          title="To date"
        />
        <button className="btn btn-ghost btn-sm" onClick={fetchEntries}>Refresh</button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {loading ? (
        <div className="loading-text"><span className="spinner" /> Loading journal...</div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">&#x1f4d3;</div>
          <div className="empty-state-text">No journal entries yet. Start by analyzing your trading thoughts in the Chat tab.</div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Asset</th>
                  <th>Emotion</th>
                  <th>State</th>
                  <th>Rec.</th>
                  <th>P/L</th>
                  <th>Rating</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const isExpanded = expandedId === entry.id;

                  return (
                    <React.Fragment key={entry.id}>
                      <tr className="clickable" onClick={() => toggleExpand(entry.id)}>
                        <td style={{ whiteSpace: 'nowrap', fontSize: '0.82rem' }}>
                          {entry.timestamp ? new Date(entry.timestamp).toLocaleDateString() : '-'}
                        </td>
                        <td>{entry.asset || '-'}</td>
                        <td>
                          <span className={`badge ${emotionBadgeClass(entry.primary_emotion)}`}>
                            {entry.primary_emotion || '-'}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.82rem' }}>
                          {entry.state_label || '-'}
                        </td>
                        <td>
                          <span className={`badge ${actionBadgeClass(entry.recommended_action)}`}>
                            {entry.recommended_action ? entry.recommended_action.replace(/_/g, ' ') : '-'}
                          </span>
                        </td>
                        <td>{formatPnl(entry.pnl_after_trade)}</td>
                        <td style={{ fontSize: '0.82rem' }}>
                          {entry.outcome_rating?.replace(/_/g, ' ') || '-'}
                        </td>
                        <td>
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={(e) => { e.stopPropagation(); setReviewEntry(entry); }}
                          >
                            Review
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={8} style={{ padding: 0 }}>
                            <JournalEntry entry={entry} onReview={() => setReviewEntry(entry)} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {reviewEntry && (
        <ReviewModal
          entry={reviewEntry}
          onClose={() => setReviewEntry(null)}
          onSaved={handleReviewSaved}
        />
      )}
    </div>
  );
}
