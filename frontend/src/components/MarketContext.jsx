import React, { useState } from 'react';

const TIME_HORIZONS = ['scalp', 'day', 'swing', 'position'];
const ACTION_TYPES = ['adding', 'reducing', 'exiting', 'new'];

export default function MarketContext({ values, onChange }) {
  const [open, setOpen] = useState(false);

  function update(field, value) {
    onChange((prev) => ({ ...prev, [field]: value }));
  }

  function handleNumberChange(field, e) {
    const val = e.target.value;
    update(field, val === '' ? '' : Number(val));
  }

  const filledCount = Object.values(values).filter(
    (v) => v !== '' && v !== null && v !== undefined
  ).length;

  return (
    <div className="card" style={{ marginBottom: '0.5rem' }}>
      <button
        className="collapsible-toggle"
        onClick={() => setOpen(!open)}
        type="button"
      >
        <span className={`collapsible-arrow ${open ? 'open' : ''}`}>&#9654;</span>
        Market Context
        {filledCount > 0 && (
          <span className="badge badge-blue" style={{ marginLeft: '0.5rem' }}>
            {filledCount} field{filledCount !== 1 ? 's' : ''}
          </span>
        )}
      </button>
      {open && (
        <div style={{ marginTop: '0.75rem' }}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Asset</label>
              <input
                className="form-input"
                type="text"
                placeholder="e.g. BTC, ETH, SPY"
                value={values.asset || ''}
                onChange={(e) => update('asset', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Current Price</label>
              <input
                className="form-input"
                type="number"
                step="any"
                placeholder="0.00"
                value={values.current_price ?? ''}
                onChange={(e) => handleNumberChange('current_price', e)}
              />
            </div>
          </div>
          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Recent Move %</label>
              <input
                className="form-input"
                type="number"
                step="any"
                placeholder="-5.2"
                value={values.recent_move_pct ?? ''}
                onChange={(e) => handleNumberChange('recent_move_pct', e)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Time Horizon</label>
              <select
                className="form-select"
                value={values.time_horizon || ''}
                onChange={(e) => update('time_horizon', e.target.value)}
              >
                <option value="">Select...</option>
                {TIME_HORIZONS.map((h) => (
                  <option key={h} value={h}>{h.charAt(0).toUpperCase() + h.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Action Type</label>
              <select
                className="form-select"
                value={values.action_type || ''}
                onChange={(e) => update('action_type', e.target.value)}
              >
                <option value="">Select...</option>
                {ACTION_TYPES.map((a) => (
                  <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Position Size</label>
              <input
                className="form-input"
                type="number"
                step="any"
                placeholder="1000"
                value={values.position_size ?? ''}
                onChange={(e) => handleNumberChange('position_size', e)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Unrealized P/L</label>
              <input
                className="form-input"
                type="number"
                step="any"
                placeholder="-200"
                value={values.unrealized_pnl ?? ''}
                onChange={(e) => handleNumberChange('unrealized_pnl', e)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Invalidation Level</label>
              <input
                className="form-input"
                type="number"
                step="any"
                placeholder="Price level"
                value={values.invalidation_level ?? ''}
                onChange={(e) => handleNumberChange('invalidation_level', e)}
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Thesis</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="Brief thesis for this trade..."
              value={values.thesis || ''}
              onChange={(e) => update('thesis', e.target.value)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
