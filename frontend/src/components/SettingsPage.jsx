import React, { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../api';

const LLM_BACKENDS = [
  { value: 'ollama', label: 'Ollama' },
  { value: 'lmstudio', label: 'LM Studio' },
  { value: 'rule_based', label: 'Rule-based Only' },
];

const NOTIFICATION_STATES = [
  'fomo_buying',
  'panic_selling',
  'revenge_trading',
  'euphoria_top',
  'capitulation',
  'tilt',
];

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    llm_backend: 'ollama',
    llm_url: 'http://localhost:11434',
    model_name: 'llama3',
    telegram_bot_token: '',
    telegram_chat_id: '',
    notification_states: [],
    desktop_notifications: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getSettings();
        if (!cancelled && data) {
          setSettings((prev) => ({ ...prev, ...data }));
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load settings');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function update(field, value) {
    setSettings((prev) => ({ ...prev, [field]: value }));
  }

  function toggleNotificationState(state) {
    setSettings((prev) => {
      const current = prev.notification_states || [];
      const updated = current.includes(state)
        ? current.filter((s) => s !== state)
        : [...current, state];
      return { ...prev, notification_states: updated };
    });
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccessMsg('');
    try {
      await updateSettings(settings);
      setSuccessMsg('Settings saved successfully');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="loading-text"><span className="spinner" /> Loading settings...</div>;
  }

  return (
    <div>
      <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>Settings</h2>

      {error && <div className="error-box">{error}</div>}
      {successMsg && (
        <div style={{ background: 'var(--green-bg)', color: 'var(--green)', border: '1px solid rgba(38,166,65,0.3)', borderRadius: 'var(--radius-md)', padding: '0.6rem 1rem', fontSize: '0.9rem', marginBottom: '1rem' }}>
          {successMsg}
        </div>
      )}

      {/* LLM Configuration */}
      <div className="card">
        <div className="settings-section">
          <div className="settings-section-title">LLM Configuration</div>
          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Backend</label>
              <select
                className="form-select"
                value={settings.llm_backend}
                onChange={(e) => update('llm_backend', e.target.value)}
              >
                {LLM_BACKENDS.map((b) => (
                  <option key={b.value} value={b.value}>{b.label}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">LLM URL</label>
              <input
                className="form-input"
                type="url"
                placeholder="http://localhost:11434"
                value={settings.llm_url}
                onChange={(e) => update('llm_url', e.target.value)}
                disabled={settings.llm_backend === 'rule_based'}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Model Name</label>
              <input
                className="form-input"
                placeholder="llama3"
                value={settings.model_name}
                onChange={(e) => update('model_name', e.target.value)}
                disabled={settings.llm_backend === 'rule_based'}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Telegram */}
      <div className="card">
        <div className="settings-section">
          <div className="settings-section-title">Telegram Notifications</div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Bot Token</label>
              <input
                className="form-input"
                type="password"
                placeholder="123456:ABC-DEF..."
                value={settings.telegram_bot_token}
                onChange={(e) => update('telegram_bot_token', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Chat ID</label>
              <input
                className="form-input"
                placeholder="e.g. 123456789"
                value={settings.telegram_chat_id}
                onChange={(e) => update('telegram_chat_id', e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Notification preferences */}
      <div className="card">
        <div className="settings-section">
          <div className="settings-section-title">Notification Triggers</div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            Select which emotional states should trigger notifications:
          </p>
          <div className="checkbox-group">
            {NOTIFICATION_STATES.map((state) => (
              <label className="checkbox-label" key={state}>
                <input
                  type="checkbox"
                  checked={(settings.notification_states || []).includes(state)}
                  onChange={() => toggleNotificationState(state)}
                />
                {state.replace(/_/g, ' ')}
              </label>
            ))}
          </div>
        </div>

        <div className="settings-section" style={{ marginBottom: 0 }}>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={settings.desktop_notifications || false}
              onChange={(e) => update('desktop_notifications', e.target.checked)}
            />
            Enable desktop notifications
          </label>
        </div>
      </div>

      {/* Save */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
        <button className="btn btn-primary btn-lg" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
