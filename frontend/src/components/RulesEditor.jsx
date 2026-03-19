import React, { useState, useEffect } from 'react';
import { getRules, updateRules } from '../api';

export default function RulesEditor() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [editingIdx, setEditingIdx] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    loadRules();
  }, []);

  async function loadRules() {
    setLoading(true);
    setError(null);
    try {
      const data = await getRules();
      setRules(Array.isArray(data) ? data : data.rules || []);
    } catch (err) {
      setError(err.message || 'Failed to load rules');
    } finally {
      setLoading(false);
    }
  }

  function startEdit(idx) {
    setEditingIdx(idx);
    setEditForm({ ...rules[idx] });
    setSuccessMsg('');
  }

  function cancelEdit() {
    setEditingIdx(null);
    setEditForm({});
  }

  function updateEditField(field, value) {
    setEditForm((prev) => ({ ...prev, [field]: value }));
  }

  async function saveRule() {
    setSaving(true);
    setError(null);
    setSuccessMsg('');
    try {
      const updated = [...rules];
      updated[editingIdx] = editForm;
      await updateRules(updated);
      setRules(updated);
      setEditingIdx(null);
      setEditForm({});
      setSuccessMsg('Rule saved successfully');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to save rule');
    } finally {
      setSaving(false);
    }
  }

  async function deleteRule(idx) {
    if (!confirm('Delete this rule?')) return;
    setSaving(true);
    setError(null);
    try {
      const updated = rules.filter((_, i) => i !== idx);
      await updateRules(updated);
      setRules(updated);
      if (editingIdx === idx) cancelEdit();
      setSuccessMsg('Rule deleted');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to delete rule');
    } finally {
      setSaving(false);
    }
  }

  function addNewRule() {
    const newRule = {
      name: 'New Rule',
      conditions: '',
      action: 'WAIT',
      conviction_min: 0,
      conviction_max: 100,
      guardrails: '',
      cooldown_seconds: 0,
    };
    setRules((prev) => [...prev, newRule]);
    setEditingIdx(rules.length);
    setEditForm(newRule);
  }

  async function resetDefaults() {
    if (!confirm('Reset all rules to defaults? This cannot be undone.')) return;
    setSaving(true);
    setError(null);
    try {
      await updateRules({ reset: true });
      await loadRules();
      setSuccessMsg('Rules reset to defaults');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to reset rules');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="loading-text"><span className="spinner" /> Loading rules...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Trading Rules</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-ghost btn-sm" onClick={resetDefaults} disabled={saving}>
            Reset Defaults
          </button>
          <button className="btn btn-primary btn-sm" onClick={addNewRule}>
            + Add Rule
          </button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {successMsg && (
        <div style={{ background: 'var(--green-bg)', color: 'var(--green)', border: '1px solid rgba(38,166,65,0.3)', borderRadius: 'var(--radius-md)', padding: '0.6rem 1rem', fontSize: '0.9rem', marginBottom: '1rem' }}>
          {successMsg}
        </div>
      )}

      {rules.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">&#x1f4cb;</div>
          <div className="empty-state-text">No rules configured. Add a rule or reset to defaults.</div>
        </div>
      ) : (
        rules.map((rule, idx) => (
          <div className="rule-card" key={idx}>
            {editingIdx === idx ? (
              /* Edit mode */
              <div>
                <div className="form-group">
                  <label className="form-label">Rule Name</label>
                  <input
                    className="form-input"
                    value={editForm.name || ''}
                    onChange={(e) => updateEditField('name', e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Conditions (JSON)</label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    placeholder='{"state": "panic-selling", "intensity_min": 50}'
                    value={typeof editForm.conditions === 'object' ? JSON.stringify(editForm.conditions) : editForm.conditions || ''}
                    onChange={(e) => {
                      try { updateEditField('conditions', JSON.parse(e.target.value)); }
                      catch { updateEditField('conditions', e.target.value); }
                    }}
                  />
                </div>
                <div className="form-row-3">
                  <div className="form-group">
                    <label className="form-label">Action</label>
                    <select
                      className="form-select"
                      value={editForm.action || ''}
                      onChange={(e) => updateEditField('action', e.target.value)}
                    >
                      <option value="">Select...</option>
                      {['BUY', 'SELL', 'HOLD', 'WAIT', 'NO TRADE', 'REDUCE'].map((a) => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Conviction Min</label>
                    <input
                      className="form-input"
                      type="number"
                      min="0"
                      max="100"
                      value={editForm.conviction_min ?? ''}
                      onChange={(e) => updateEditField('conviction_min', e.target.value === '' ? '' : Number(e.target.value))}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Conviction Max</label>
                    <input
                      className="form-input"
                      type="number"
                      min="0"
                      max="100"
                      value={editForm.conviction_max ?? ''}
                      onChange={(e) => updateEditField('conviction_max', e.target.value === '' ? '' : Number(e.target.value))}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Guardrails</label>
                    <input
                      className="form-input"
                      placeholder="Comma-separated guardrails"
                      value={editForm.guardrails || ''}
                      onChange={(e) => updateEditField('guardrails', e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Cooldown (seconds)</label>
                    <input
                      className="form-input"
                      type="number"
                      min="0"
                      value={editForm.cooldown_seconds ?? ''}
                      onChange={(e) => updateEditField('cooldown_seconds', e.target.value === '' ? '' : Number(e.target.value))}
                    />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                  <button className="btn btn-primary btn-sm" onClick={saveRule} disabled={saving}>
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={cancelEdit} disabled={saving}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              /* Display mode */
              <div>
                <div className="rule-card-header">
                  <span className="rule-name">{rule.name || 'Unnamed Rule'}</span>
                  <div style={{ display: 'flex', gap: '0.35rem' }}>
                    <button className="btn btn-ghost btn-sm" onClick={() => startEdit(idx)}>Edit</button>
                    <button className="btn btn-ghost btn-sm" style={{ color: 'var(--red)' }} onClick={() => deleteRule(idx)}>Delete</button>
                  </div>
                </div>
                {rule.conditions && (
                  <div className="rule-detail"><strong>Conditions:</strong> {typeof rule.conditions === 'object' ? JSON.stringify(rule.conditions) : rule.conditions}</div>
                )}
                <div className="rule-detail">
                  <strong>Action:</strong>{' '}
                  <span className={`badge ${actionBadgeClass(rule.action)}`}>
                    {rule.action || '-'}
                  </span>
                </div>
                {rule.conviction_range && (
                  <div className="rule-detail">
                    <strong>Conviction:</strong> {Array.isArray(rule.conviction_range) ? `${rule.conviction_range[0]} - ${rule.conviction_range[1]}` : rule.conviction_range}
                  </div>
                )}
                {rule.guardrails && (
                  <div className="rule-detail"><strong>Guardrails:</strong> {Array.isArray(rule.guardrails) ? rule.guardrails.join(', ') : rule.guardrails}</div>
                )}
                {(rule.cooldown > 0 || rule.cooldown_seconds > 0) && (
                  <div className="rule-detail"><strong>Cooldown:</strong> {rule.cooldown || rule.cooldown_seconds}m</div>
                )}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function actionBadgeClass(action) {
  if (!action) return 'badge-muted';
  const a = action.toLowerCase();
  if (a.includes('buy')) return 'badge-green';
  if (a.includes('sell')) return 'badge-red';
  if (a.includes('wait') || a.includes('hold')) return 'badge-yellow';
  return 'badge-muted';
}
