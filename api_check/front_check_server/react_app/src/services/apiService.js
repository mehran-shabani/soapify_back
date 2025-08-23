/**
 * Minimal apiService stub so tests compile.
 * Replace with actual implementation. Exposes get/post/put/patch/delete and optional configure.
 */
const state = { baseURL: '' };
const buildUrl = (path, params) => {
  const base = state.baseURL ? state.baseURL.replace(/\/+$/,'') : '';
  const p = String(path || '').replace(/^\/+/, '');
  const u = base ? `${base}/${p}` : `/${p}`;
  if (params && typeof params === 'object') {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k,v]) => {
      if (Array.isArray(v)) v.forEach(it => qs.append(k, String(it)));
      else if (v === null || v === undefined) { /* omit */ }
      else qs.append(k, String(v));
    });
    const q = qs.toString();
    return q ? `${u}?${q}` : u;
  }
  return u;
};

const parse = async (resp) => {
  const ct = resp.headers && resp.headers.get ? resp.headers.get('content-type') : '';
  if (!resp.ok) {
    let body;
    try { body = ct && /json/i.test(ct) ? await resp.json() : await resp.text(); } catch(e){ body = undefined; }
    const err = Object.assign(new Error(`HTTP ${resp.status}`), { status: resp.status, body });
    throw err;
  }
  if (ct && /json/i.test(ct)) return resp.json();
  return resp.text();
};

const configure = (cfg = {}) => {
  if (cfg.baseURL) state.baseURL = cfg.baseURL;
};

const request = (method) => async (path, { params, data, headers, signal } = {}) => {
  const url = buildUrl(path, params);
  const init = { method: method.toUpperCase(), headers: { ...(headers || {}) } };
  if (data !== undefined) {
    init.headers['Content-Type'] = init.headers['Content-Type'] || 'application/json';
    init.body = typeof data === 'string' ? data : JSON.stringify(data);
  }
  if (signal) init.signal = signal;
  const resp = await fetch(url, init);
  return parse(resp);
};

module.exports = {
  configure,
  get: request('GET'),
  post: request('POST'),
  put: request('PUT'),
  patch: request('PATCH'),
  delete: request('DELETE'),
};