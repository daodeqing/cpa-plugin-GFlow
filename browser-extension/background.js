// background.js - GFlow login helper background service
importScripts('common.js');

const ALARM = 'gflow-cookie-sync';
const FLOW_URL = 'https://flow.google.com/projects';
let activeSync = null;

// Logging
const Logger = {
  async log(level, message, details = null) {
    const timestamp = new Date().toISOString();
    const safeDetails = sanitizeLogDetails(details);
    const logEntry = { timestamp, level, message, details: safeDetails };
    console.log(`[${level}] ${message}`, safeDetails || '');
    try {
      const { logs = [] } = await chrome.storage.local.get(['logs']);
      const updatedLogs = [logEntry, ...logs].slice(0, 100);
      await chrome.storage.local.set({ logs: updatedLogs });
    } catch (_) {}
  },
  info(msg, d) { return this.log('INFO', msg, d); },
  error(msg, d) { return this.log('ERROR', msg, d); },
  success(msg, d) { return this.log('SUCCESS', msg, d); },
  async getLogs() {
    const { logs = [] } = await chrome.storage.local.get(['logs']);
    return logs;
  },
  async clearLogs() {
    await chrome.storage.local.set({ logs: [] });
  }
};

function sanitizeLogDetails(value, key = '') {
  if (value == null) return value;
  if (/^(authorization|connectionToken|google_cookies|session_token|password|secret)$/i.test(key)) {
    return '[REDACTED]';
  }
  if (Array.isArray(value)) return value.map(item => sanitizeLogDetails(item));
  if (typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, sanitizeLogDetails(v, k)])
    );
  }
  if (typeof value === 'string') {
    return value
      .replace(/Bearer\s+[^\s]+/gi, 'Bearer [REDACTED]')
      .replace(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/gi, email => email[0] + '***@' + email.split('@')[1])
      .replace(/((?:^|[;\s])(?:__Secure-)?(?:OSID|SID|HSID|SSID|APISID|SAPISID)=)[^;\s]+/gi, '$1[REDACTED]');
  }
  return value;
}

function safeServerDiagnostic(raw) {
  const result = {};
  if (['bootstrap', 'rpc'].includes(raw?.phase)) result.phase = raw.phase;
  if (['nzlxg', 'jHPbke'].includes(raw?.rpc)) result.rpc = raw.rpc;
  if (['redirect', 'http_auth', 'missing_metadata'].includes(raw?.reason)) result.reason = raw.reason;
  for (const key of ['http_status', 'rpc_code', 'browser_http_status', 'browser_rpc_code']) {
    if (Number.isInteger(raw?.[key]) && raw[key] >= 0 && raw[key] < 600) result[key] = raw[key];
  }
  for (const key of ['bootstrap_identity', 'xsrf_present', 'account_matches', 'browser_credit_ok', 'observed_cookie_header']) {
    if (typeof raw?.[key] === 'boolean') result[key] = raw[key];
  }
  for (const key of ['rpc_cookie_count', 'duplicate_cookie_names']) {
    if (Number.isInteger(raw?.[key]) && raw[key] >= 0 && raw[key] <= 1000) result[key] = raw[key];
  }
  return result;
}

async function publicState() {
  const state = await chrome.storage.local.get(['config', 'lastSync']);
  const config = state.config || {};
  return {
    configured: Boolean(config.connectionToken),
    loginAccount: config.loginAccount || '',
    apiUrl: config.apiUrl || '',
    autoSync: config.autoSync !== false,
    lastSync: state.lastSync || null
  };
}

async function restoreAlarm() {
  const { config } = await chrome.storage.local.get('config');
  await chrome.alarms.clear(ALARM);
  if (config?.connectionToken && config.autoSync) {
    await chrome.alarms.create(ALARM, { periodInMinutes: 60 });
  }
}

async function saveConfiguration(input) {
  const state = await chrome.storage.local.get('config');
  const connection = validateConnection(input.connection || state.config);
  const config = {
    ...connection,
    loginAccount: validateEmail(input.loginAccount),
    autoSync: Boolean(input.autoSync)
  };
  if (!await chrome.permissions.contains({ origins: [connectionPermission(config.apiUrl)] })) {
    throw new Error('Allow the extension to connect to local GFlow');
  }
  await chrome.storage.local.set({ config });
  await restoreAlarm();
  await Logger.info('GFlow connection settings saved', { apiUrl: config.apiUrl, loginAccount: config.loginAccount });
  return publicState();
}

async function waitForTabReady(tabId, maxWaitMs = 15000) {
  const startTime = Date.now();
  while (Date.now() - startTime < maxWaitMs) {
    try {
      const tab = await chrome.tabs.get(tabId);
      if (tab && tab.status === 'complete') return tab;
    } catch (_) {
      break;
    }
    await new Promise(r => setTimeout(r, 500));
  }
}

async function closeTemporaryTab(tab) {
  if (tab && typeof tab.id === 'number') {
    try { await chrome.tabs.remove(tab.id); } catch (_) {}
  }
}

// Listen only for nzlxg requests from this temporary tab; Cookies remain in memory only.
async function readObservedFlowCookies(tabId, email) {
  if (!chrome.webRequest?.onBeforeSendHeaders) throw new Error('Reload the GFlow login helper to enable request reading permissions');
  let cookieHeader='';
  const listener = details => {
    const url=new URL(details.url);
    if (details.tabId !== tabId || details.method !== 'POST' || url.origin !== 'https://flow.google.com'
        || url.pathname !== '/_/AiSandboxAngularFrontend/data/batchexecute' || url.searchParams.get('rpcids') !== 'nzlxg') return;
    cookieHeader=(details.requestHeaders || []).find(header=>header.name.toLowerCase()==='cookie')?.value || '';
  };
  chrome.webRequest.onBeforeSendHeaders.addListener(listener,
    {urls:['https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute*'],tabId}, ['requestHeaders','extraHeaders']);
  try {
    const diagnostic = await chrome.tabs.sendMessage(tabId, {action:'gflow-credit-check',email});
    // Preserve the actual browser order and same-name Cookies; reject empty values and message control characters.
    if (!cookieHeader || cookieHeader.length > 262144 || /[\x00-\x1f\x7f]/.test(cookieHeader)) {
      throw new Error('Chrome did not provide Cookies for this Flow request. Allow the new permissions on the extension management page and retry');
    }
    const safe = {success:diagnostic?.success === true};
    if (['identity','network','rpc'].includes(diagnostic?.phase)) safe.phase=diagnostic.phase;
    for (const key of ['http_status','rpc_code']) if (Number.isInteger(diagnostic?.[key]) && diagnostic[key]>=0 && diagnostic[key]<600) safe[key]=diagnostic[key];
    return {cookieHeader,diagnostic:safe};
  } finally {
    chrome.webRequest.onBeforeSendHeaders.removeListener(listener);
  }
}

async function executeSync() {
  const { config } = await chrome.storage.local.get('config');
  if (!config) throw new Error('Copy the config from GFlow and save it first');
  const connection = validateConnection(config);
  const loginAccount = validateEmail(config.loginAccount);

  await Logger.info('Syncing GFlow login credentials...', { account: loginAccount });

  // Fix the window and Cookie store for this sync so the background tab and reads use the same window.
  const sourceTabs = chrome.tabs?.query ? await chrome.tabs.query({ active: true, currentWindow: true }) : [];
  const sourceTab = sourceTabs[0];
  let storeId;
  if (sourceTab && chrome.cookies?.getAllCookieStores) {
    const stores = await chrome.cookies.getAllCookieStores();
    storeId = stores.find(item => item.tabIds.includes(sourceTab.id))?.id;
    if (!storeId) throw new Error('Cannot determine the login session for this window. Reopen the helper in the Flow window');
  }
  let tempTab = null;
  let rawCookies, frontend, observed;
  let pageUrl = FLOW_URL;
  try {
    const current = new URL(sourceTab?.url || '');
    if (current.origin === 'https://flow.google.com' && /^\/project\/[a-f0-9-]{36}$/.test(current.pathname)) pageUrl = current.origin + current.pathname;
  } catch (_) {}
  try {
    if (chrome.tabs?.create && chrome.tabs?.get) {
      await Logger.info('Refreshing the Flow login session in the background...');
      tempTab = await chrome.tabs.create({ url: pageUrl, active: false,
        ...(Number.isInteger(sourceTab?.windowId) ? { windowId: sourceTab.windowId } : {}) });
      const loadedTab = await waitForTabReady(tempTab.id);
      if (!loadedTab) throw new Error('Flow page load timed out. Confirm the website opens and retry');
      if (new URL(loadedTab.url || '').hostname !== 'flow.google.com') {
        throw new Error('The Flow page requires login. Log in in the current browser first');
      }
      await new Promise(resolve => setTimeout(resolve, 5000));
      if (chrome.tabs.sendMessage) {
        let session;
        try { session = await chrome.tabs.sendMessage(tempTab.id, {action:'gflow-page-session',email:loginAccount}); }
        catch (_) { throw new Error('Cannot read the Flow page login session. Reload the helper and retry'); }
        if (!session?.signed_in) throw new Error('The Flow page returned no logged-in account. Log in to Flow again in the current browser before syncing');
        if (session.account_matches !== true) throw new Error('The current Flow account does not match the helper email. Check the email or use a separate browser profile');
        if (!session.frontend) throw new Error('Flow page authentication fields are incomplete. Refresh Flow and retry');
        frontend = session.frontend;
        observed = await readObservedFlowCookies(tempTab.id, loginAccount);
        await Logger.info('Flow browser credits check completed', observed.diagnostic);
      }
      // Determine the store from the actual warmup tab, including scheduled syncs without an active tab.
      if (chrome.cookies?.getAllCookieStores) {
        const stores = await chrome.cookies.getAllCookieStores();
        const warmedStore = stores.find(item => item.tabIds.includes(tempTab.id));
        if (!warmedStore || (storeId && storeId !== warmedStore.id)) {
          throw new Error('The Flow page and current window login sessions differ. Sync from the Flow window');
        }
        storeId = warmedStore.id;
      }
    }
    if (!observed) {
      // Support tests/older browsers without the page messaging API; current Chrome uses actual request headers.
      const scopes = [FLOW_URL, 'https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute'];
      const groups = [];
      for (const url of scopes) {
        groups.push(await chrome.cookies.getAll({ url, ...(storeId ? { storeId } : {}) }));
      }
      rawCookies = groups.flat();
    }
    const googleCookies = observed?.cookieHeader || serializeFlowCookies(rawCookies);
    await Logger.info('Cookies extracted; submitting to the local GFlow core...');

    const payload = {
      login_account: loginAccount,
      google_cookies: googleCookies,
      protocol_mode: 'protocol',
      user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
      ...(frontend ? {frontend} : {}),
      ...(observed ? {browser_check:observed.diagnostic,cookie_source:'browser_request'} : {})
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120000);
    let response;
    try {
      response = await fetch(connection.apiUrl, {
        method: 'POST',
        redirect: 'error',
        cache: 'no-store',
        credentials: 'omit',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + connection.connectionToken
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
    } catch (error) {
      const errText = error.name === 'AbortError' ? 'GFlow sync timed out. Check proxy settings and retry' : 'Cannot connect to local GFlow. Confirm the EasyCPA core is running';
      await Logger.error(errText);
      throw new Error(errText);
    } finally {
      clearTimeout(timer);
    }

    let result = null;
    try { result = await response.json(); } catch (_) {}
    if (!response.ok || result?.success !== true) {
      if (response.status === 401 || response.status === 403) {
        await Logger.error('Connection credentials expired');
        throw new Error('Connection credentials expired. Copy the extension config from GFlow again');
      }
      if (response.status === 404) {
        await Logger.error('API not found');
        throw new Error('This GFlow version does not support extension sync. Update the plugin');
      }
      const detail = result?.error;
      const safeMessage = typeof detail?.message === 'string'
        && detail.message.length <= 500
        && !/(cookie\s*[:=]|bearer\s|connectionToken|access_token|https?:\/\/|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})/i.test(detail.message)
        ? detail.message : null;
      const code = /^gflow_[a-z_]+$/.test(detail?.code || '') ? detail.code : null;
      const errorMsg = safeMessage
        ? safeMessage + (code ? ' [' + code + ']' : '')
        : 'GFlow sync failed (HTTP ' + response.status + '). Check the logs for detailed diagnostics.';
      await Logger.error('Sync failed', { error: errorMsg, diagnostic: safeServerDiagnostic(detail?.diagnostic) });
      throw new Error(errorMsg);
    }

    const actionMsg = result.action === 'updated' ? 'GFlow account login session updated' : 'GFlow account added';
    await Logger.success(`✅ ${actionMsg}`, { action: result.action });
    return { success: true, action: result.action, message: actionMsg };
  } finally {
    await closeTemporaryTab(tempTab);
  }
}

function syncNow() {
  if (activeSync) return activeSync;
  activeSync = (async () => {
    let result;
    try {
      result = await executeSync();
    } catch (error) {
      result = { success: false, message: error.message };
    }
    await chrome.storage.local.set({
      lastSync: { success: result.success, message: result.message, timestamp: Date.now() }
    });
    if (chrome.action?.setBadgeText) {
      await chrome.action.setBadgeText({ text: result.success ? 'OK' : '!' });
      await chrome.action.setBadgeBackgroundColor({ color: result.success ? '#0d9488' : '#dc2626' });
    }
    return result;
  })().finally(() => { activeSync = null; });
  return activeSync;
}

chrome.runtime.onMessage.addListener((request, sender, respond) => {
  if (sender.id !== chrome.runtime.id) return false;
  const action = request.action;
  if (action === 'state' || action === 'getConfig') {
    publicState().then(result => respond({ ok: true, success: true, result, config: result }), () => respond({ ok: false, success: false }));
    return true;
  }
  if (action === 'save' || action === 'saveConfig') {
    saveConfiguration(request.config).then(result => respond({ ok: true, success: true, result, config: result }), e => respond({ ok: false, success: false, message: e.message, error: e.message }));
    return true;
  }
  if (action === 'sync' || action === 'testNow') {
    syncNow().then(result => respond({ ok: true, success: result.success, result, ...result }), e => respond({ ok: false, success: false, message: e.message, error: e.message }));
    return true;
  }
  if (action === 'forget') {
    chrome.storage.local.remove(['config', 'lastSync'])
      .then(restoreAlarm)
      .then(publicState)
      .then(result => respond({ ok: true, result }), () => respond({ ok: false }));
    return true;
  }
  if (action === 'getLogs') {
    Logger.getLogs().then(logs => respond({ ok: true, success: true, logs }), () => respond({ ok: false, logs: [] }));
    return true;
  }
  if (action === 'clearLogs') {
    Logger.clearLogs().then(() => respond({ ok: true, success: true }), () => respond({ ok: false }));
    return true;
  }
  return false;
});

if (chrome.alarms?.onAlarm) {
  chrome.alarms.onAlarm.addListener(alarm => { if (alarm.name === ALARM) void syncNow(); });
}
if (chrome.runtime?.onStartup) {
  chrome.runtime.onStartup.addListener(() => { void restoreAlarm(); });
}
if (chrome.runtime?.onInstalled) {
  chrome.runtime.onInstalled.addListener(() => { void restoreAlarm(); });
}