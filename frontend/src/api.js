const BASE_URL = '/api';

async function request(url, options = {}) {
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };

  const response = await fetch(`${BASE_URL}${url}`, config);

  if (!response.ok) {
    const errorBody = await response.text().catch(() => '');
    throw new Error(
      `API error ${response.status}: ${response.statusText}${errorBody ? ` - ${errorBody}` : ''}`
    );
  }

  return response.json();
}

export async function analyzeMessage(text, marketContext) {
  return request('/analyze', {
    method: 'POST',
    body: JSON.stringify({ text, market_context: marketContext }),
  });
}

export async function getJournal(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, value);
    }
  });
  const query = params.toString();
  return request(`/journal${query ? `?${query}` : ''}`);
}

export async function getEntry(id) {
  return request(`/journal/${id}`);
}

export async function reviewEntry(id, data) {
  return request(`/journal/${id}/review`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function overrideEntry(id, action) {
  return request(`/journal/${id}/override`, {
    method: 'POST',
    body: JSON.stringify({ entry_id: id, override_action: action }),
  });
}

export async function getStats() {
  return request('/stats');
}

export async function getRules() {
  return request('/rules');
}

export async function updateRules(rules) {
  return request('/rules', {
    method: 'PUT',
    body: JSON.stringify(rules),
  });
}

export async function getSettings() {
  return request('/settings');
}

export async function updateSettings(settings) {
  return request('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

export async function healthCheck() {
  return request('/health');
}
