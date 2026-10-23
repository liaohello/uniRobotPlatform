import { mountIntegration } from './panel.js';
import { mountDraftEditor } from './drafts.js';

async function api(path, method = 'GET', body) {
  const response = await fetch(path, {
    method, cache: 'no-store', headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const value = await response.json();
  if (!response.ok) {
    const detail = value.detail;
    const message = Array.isArray(detail)
      ? detail.map(item => `${item.loc.join('.')}: ${item.msg}`).join('; ')
      : detail?.message ?? detail ?? `HTTP ${response.status}`;
    throw new Error(message);
  }
  return value;
}

const draftsPath = '/api/v1/experiment-drafts';
mountDraftEditor(document.querySelector('#draft-editor'), {
  service: {
    list: () => api(draftsPath),
    get: id => api(`${draftsPath}/${encodeURIComponent(id)}`),
    create: payload => api(draftsPath, 'POST', payload),
    save: (id, payload) => api(`${draftsPath}/${encodeURIComponent(id)}`, 'PUT', payload),
    validate: (id, payload) => api(`${draftsPath}/${encodeURIComponent(id)}/validate`, 'POST', payload),
  },
});

mountIntegration(document.querySelector('#integration'), {
  async loadPreflight(signal) {
    const response = await fetch('/api/v1/mobilecar/preflight', { signal, cache: 'no-store' });
    if (!response.ok) throw new Error(`接入服务返回 HTTP ${response.status}`);
    return response.json();
  },
});
