const API_BASE = (window.VERITAS_CONFIG && window.VERITAS_CONFIG.API_BASE) || '/api/v1';
const TOKEN_KEY = 'veritas_access_token';
const REFRESH_KEY = 'veritas_refresh_token';

const state = {
  currentUser: null,
  currentView: 'dashboard',
  datasets: {},
  summary: null,
};

const modules = [
  { id: 'dashboard', label: 'Dashboard', group: 'Platform' },
  { id: 'ident', label: 'IDENT™ Registry', group: 'Core' },
  { id: 'projects', label: 'TWIN™ Projects', group: 'Core' },
  { id: 'build', label: 'BUILD™ Evidence', group: 'Core' },
  { id: 'vision', label: 'VISION™ Inspections', group: 'Core' },
  { id: 'pay', label: 'PAY™ Escrow', group: 'Core' },
  { id: 'seal', label: 'SEAL™ Certification', group: 'Core' },
  { id: 'market', label: 'MARKET™ Tenders', group: 'Expansion' },
  { id: 'origin', label: 'ORIGIN™ Materials', group: 'Expansion' },
  { id: 'monitor', label: 'MONITOR™ Live', group: 'Expansion' },
  { id: 'lex', label: 'LEX™ Arbitration', group: 'Expansion' },
  { id: 'atlas', label: 'ATLAS™ Intelligence', group: 'Institution' },
  { id: 'verifund', label: 'VERIFUND™', group: 'Institution' },
  { id: 'academy', label: 'ACADEMY™', group: 'Institution' },
  { id: 'clone', label: 'CLONE™ Rollout', group: 'Institution' },
  { id: 'governance', label: 'Governance', group: 'Sovereign' },
  { id: 'regulatory', label: 'Regulatory', group: 'Sovereign' },
  { id: 'audit', label: 'Audit Trail', group: 'Sovereign' },
];

const quickCreateOptions = [
  { key: 'project', label: 'New project' },
  { key: 'component', label: 'New component' },
  { key: 'evidence', label: 'Upload evidence' },
  { key: 'inspection', label: 'Record inspection' },
  { key: 'tender', label: 'Publish tender' },
  { key: 'report', label: 'Publish ATLAS report' },
  { key: 'product', label: 'Create VERIFUND product' },
  { key: 'application', label: 'Create underwriting application' },
  { key: 'path', label: 'Create learning path' },
  { key: 'course', label: 'Create course' },
];

const el = {};
document.querySelectorAll('[id]').forEach(node => { el[node.id] = node; });

function token(){ return localStorage.getItem(TOKEN_KEY); }
function refreshToken(){ return localStorage.getItem(REFRESH_KEY); }
function saveTokens(payload){
  localStorage.setItem(TOKEN_KEY, payload.access_token);
  if (payload.refresh_token) localStorage.setItem(REFRESH_KEY, payload.refresh_token);
}
function clearTokens(){
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function toast(message, type='info'){
  const box = document.createElement('div');
  box.className = `toast ${type}`;
  box.textContent = message;
  el.toastContainer.appendChild(box);
  setTimeout(() => box.remove(), 3400);
}

function fmt(value){ return value ?? value === 0 ? String(value) : '—'; }
function num(value){ return typeof value === 'number' ? new Intl.NumberFormat().format(value) : fmt(value); }
function money(value, currency='USD'){
  if (value == null) return '—';
  return `${currency} ${new Intl.NumberFormat().format(value)}`;
}
function dateFmt(value){
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
}
function dateTimeFmt(value){
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-GB');
}
function itemsOf(data){ return Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []; }
function safeCount(data){ return itemsOf(data).length; }

function badgeClass(status=''){
  const s = String(status).toLowerCase();
  if (['active','approved','verified','published','released','complete','completed','passed','issued','pending_ceremony','awarded'].includes(s)) return 'green';
  if (['review','pending','submitted','open','pilot','draft','market_activation','regulatory_alignment'].includes(s)) return 'amber';
  if (['suspended','blocked','locked','failed','critical'].includes(s)) return 'red';
  if (['institutional','enterprise','honor','trusted'].includes(s)) return 'gold';
  return 'blue';
}
function badge(text){ return `<span class="badge ${badgeClass(text)}">${fmt(text)}</span>`; }

async function request(path, options={}){
  const headers = new Headers(options.headers || {});
  const isFormData = options.body instanceof FormData;
  if (!isFormData && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (token()) headers.set('Authorization', `Bearer ${token()}`);
  let response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401 && refreshToken()) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers.set('Authorization', `Bearer ${token()}`);
      response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    }
  }
  let payload = null;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
  return payload;
}

async function tryRefresh(){
  try {
    const payload = await fetch(`${API_BASE}/auth/refresh`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ refresh_token: refreshToken() })
    }).then(r => r.json().then(body => ({ ok:r.ok, body })));
    if (!payload.ok) {
      clearTokens();
      return false;
    }
    saveTokens(payload.body);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

function bind(){
  el.loginForm.addEventListener('submit', onLogin);
  el.logoutButton.addEventListener('click', logout);
  el.refreshButton.addEventListener('click', loadAllData);
  el.closeModal.addEventListener('click', closeModal);
  el.modal.addEventListener('click', (event) => { if (event.target === el.modal) closeModal(); });
  el.openQuickCreate.addEventListener('click', () => openQuickCreateModal());
}

function logout(){
  clearTokens();
  state.currentUser = null;
  el.appShell.classList.add('hidden');
  el.loginOverlay.classList.add('open');
  toast('Logged out.', 'info');
}

async function onLogin(event){
  event.preventDefault();
  el.loginMessage.textContent = 'Authenticating...';
  try {
    const payload = await request('/auth/login', {
      method:'POST',
      body: JSON.stringify({ email: el.emailInput.value.trim(), password: el.passwordInput.value })
    });
    saveTokens(payload);
    el.loginMessage.textContent = '';
    await bootstrapApp();
  } catch (error) {
    el.loginMessage.textContent = error.message;
  }
}

async function bootstrapApp(){
  try {
    state.currentUser = await request('/auth/me');
    el.profileName.textContent = state.currentUser.name;
    el.profileMeta.textContent = `${String(state.currentUser.role).toUpperCase()} • ${state.currentUser.band || '—'} • PRI ${fmt(state.currentUser.pri_score)}`;
    el.loginOverlay.classList.remove('open');
    el.appShell.classList.remove('hidden');
    renderNav();
    await loadAllData();
  } catch (error) {
    clearTokens();
    el.loginOverlay.classList.add('open');
    el.appShell.classList.add('hidden');
    toast(`Unable to start app: ${error.message}`, 'error');
  }
}

function renderNav(){
  const groups = [...new Set(modules.map(item => item.group))];
  const unread = safeCount(state.datasets.notifications?.items?.filter?.(n => !n.read) || itemsOf(state.datasets.notifications).filter(n => !n.read));
  el.sidebarNav.innerHTML = groups.map(group => {
    const nodes = modules.filter(item => item.group === group).map(item => {
      const active = state.currentView === item.id ? 'active' : '';
      const badgeText = item.id === 'dashboard' ? '' : item.id === 'audit' ? num(safeCount(state.datasets.audit)) : item.id === 'market' ? num(safeCount(state.datasets.tenders)) : item.id === 'projects' ? num(safeCount(state.datasets.projects)) : item.id === 'ident' ? num(safeCount(state.datasets.professionals)) : item.id === 'build' ? num(safeCount(state.datasets.evidence)) : item.id === 'vision' ? num(safeCount(state.datasets.inspections)) : item.id === 'pay' ? num(safeCount(state.datasets.payments)) : item.id === 'monitor' ? num(safeCount(state.datasets.alerts) + safeCount(state.datasets.sensors)) : item.id === 'dashboard' ? '' : item.id === 'dashboard' ? '' : item.id === 'dashboard' ? '' : '';
      const specialBadge = item.id === 'dashboard' && unread ? `<span class="nav-badge">${unread}</span>` : badgeText ? `<span class="nav-badge">${badgeText}</span>` : '';
      return `<button class="nav-item ${active}" data-view="${item.id}" type="button"><span>${item.label}</span>${specialBadge}</button>`;
    }).join('');
    return `<div class="nav-group"><div class="nav-label">${group}</div>${nodes}</div>`;
  }).join('');
  document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click', () => {
    state.currentView = button.dataset.view;
    renderNav();
    renderView();
  }));
}

async function loadAllData(){
  try {
    const endpoints = {
      summary: '/dashboard/summary',
      professionals: '/professionals',
      projects: '/projects',
      components: '/components',
      evidence: '/evidence',
      inspections: '/vision/inspections',
      milestones: '/payments/milestones',
      payments: '/payments/payments',
      tenders: '/tenders',
      materials: '/materials',
      certifications: '/seal/certifications',
      sensors: '/monitor/sensors',
      alerts: '/monitor/alerts',
      disputes: '/lex/disputes',
      atlas: '/atlas/portfolio/overview',
      atlasReports: '/atlas/reports',
      verifundProducts: '/verifund/products',
      verifundApps: '/verifund/applications',
      academyPaths: '/academy/paths',
      academyCourses: '/academy/courses',
      academyCredentials: '/academy/credentials',
      academyAdvancement: '/academy/advancement/me',
      cloneSummary: '/clone/rollout/summary',
      governanceDashboard: '/governance/dashboard',
      governanceMembers: '/governance/cst-members',
      governanceResolutions: '/governance/resolutions',
      regulatoryReadiness: '/regulatory/readiness',
      regulations: '/regulatory/regulations',
      consultations: '/regulatory/consultations',
      complianceMappings: '/regulatory/compliance-mappings',
      notifications: '/notifications',
      audit: '/audit'
    };
    const entries = await Promise.all(Object.entries(endpoints).map(async ([key, path]) => {
      try { return [key, await request(path)]; }
      catch (error) { return [key, { __error: error.message }]; }
    }));
    state.datasets = Object.fromEntries(entries);
    state.summary = state.datasets.summary?.__error ? null : state.datasets.summary;
    renderNav();
    renderView();
    toast('Platform data refreshed.', 'success');
  } catch (error) {
    toast(`Refresh failed: ${error.message}`, 'error');
  }
}

function renderView(){
  const view = state.currentView;
  const viewMap = {
    dashboard: renderDashboard,
    ident: renderIdent,
    projects: renderProjects,
    build: renderBuild,
    vision: renderVision,
    pay: renderPay,
    seal: renderSeal,
    market: renderMarket,
    origin: renderOrigin,
    monitor: renderMonitor,
    lex: renderLex,
    atlas: renderAtlas,
    verifund: renderVerifund,
    academy: renderAcademy,
    clone: renderClone,
    governance: renderGovernance,
    regulatory: renderRegulatory,
    audit: renderAudit,
  };
  const target = viewMap[view] || renderDashboard;
  const meta = modules.find(item => item.id === view) || modules[0];
  el.pageTitle.textContent = meta.label;
  el.pageEyebrow.textContent = meta.group;
  target();
}

function setHero(title, description, pills=[]){
  el.heroBanner.innerHTML = `
    <div class="hero-grid">
      <div>
        <div class="eyebrow">Canonical institutional view</div>
        <h3>${title}</h3>
        <p>${description}</p>
        <div class="hero-pills">${pills.map(text => `<div class="mini-chip">${text}</div>`).join('')}</div>
      </div>
      <div class="panel-soft" style="padding:18px;display:flex;flex-direction:column;justify-content:center;gap:10px;">
        <div class="eyebrow">Authenticated stance</div>
        <div style="font:700 1.2rem var(--font-d)">${state.currentUser?.band || '—'} • ${String(state.currentUser?.role || '').toUpperCase()}</div>
        <div class="muted">The frontend now reads and acts on live backend data rather than IndexedDB seed state alone.</div>
      </div>
    </div>`;
}

function setKpis(cards){
  el.kpiGrid.innerHTML = cards.map(card => `<div class="kpi-card"><b>${card.value}</b><span>${card.label}</span></div>`).join('');
}

function panel(title, eyebrow, body, action=''){
  return `<section class="card"><div class="card-head"><div><div class="eyebrow">${eyebrow}</div><h3>${title}</h3></div>${action}</div>${body}</section>`;
}

function listTemplate(items, mapper, empty='No records found.'){
  if (!items.length) return `<div class="empty">${empty}</div>`;
  return `<div class="list">${items.map(mapper).join('')}</div>`;
}

function row(title, sub, status, actions=''){
  return `<div class="list-item"><div class="list-item-top"><div><div class="list-item-title">${title}</div><div class="list-item-sub">${sub || '—'}</div></div><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">${status ? badge(status) : ''}${actions}</div></div></div>`;
}

function table(columns, rows){
  if (!rows.length) return `<div class="empty">No records found.</div>`;
  return `<div class="table-wrap"><table><thead><tr>${columns.map(col => `<th>${col}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

function cardStats(stats){
  return `<div class="stat-strip">${stats.map(item => `<div class="stat-block"><strong>${item.value}</strong><span>${item.label}</span></div>`).join('')}</div>`;
}

function renderDashboard(){
  const notifications = itemsOf(state.datasets.notifications).slice(0,5);
  const projects = itemsOf(state.datasets.projects);
  const certifications = itemsOf(state.datasets.certifications);
  const atlas = state.datasets.atlas || {};
  setHero(
    'Structural truth cannot be negotiated. It must be proven.',
    'This dashboard preserves the doctrine of your original prototype while drawing directly from the live institutional backend: project state, evidence posture, SHI activity, escrow, certification, rollout, governance, and regulatory readiness.',
    [`${safeCount(projects)} projects`, `${safeCount(itemsOf(state.datasets.professionals))} professionals`, `${safeCount(itemsOf(state.datasets.tenders))} tenders`, `${safeCount(notifications.filter(n => !n.read))} unread alerts`]
  );
  setKpis([
    { label:'Total projects', value:num(state.summary?.total_projects ?? safeCount(projects)) },
    { label:'Average SHI', value:fmt(state.summary?.avg_shi) },
    { label:'Certified projects', value:num(safeCount(certifications)) },
    { label:'Portfolio value', value:money(state.summary?.total_project_value_usd, 'USD') }
  ]);

  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Lighthouse portfolio', 'Projects', table(
          ['Project','Country','Phase','SHI','Status'],
          projects.slice(0,8).map(p => `<tr data-project="${p.uid}"><td><button class="link-btn" data-project-detail="${p.uid}">${p.name}</button><div class="muted small code">${p.uid}</div></td><td>${fmt(p.country)}</td><td>${fmt(p.phase)}</td><td>${fmt(p.shi)}</td><td>${badge(p.status)}</td></tr>`)
        ), `<button class="btn btn-sm" data-open-create="project">New project</button>`)}

        ${panel('Unread doctrine signals', 'Notifications', listTemplate(notifications, n => row(n.type || 'Notification', n.message, n.priority, !n.read ? `<button class="btn btn-sm btn-ghost" data-mark-read="${n.id}">Mark read</button>` : ''), 'No notifications yet.'), '')}
      </div>
      <div class="stack">
        ${panel('Institutional posture', 'Portfolio intelligence', cardStats([
          { label:'Countries active', value:num(atlas.countries_active) },
          { label:'Unread alerts', value:num(state.summary?.unread_notifications) },
          { label:'Tender pipeline', value:num(state.summary?.open_tenders) },
          { label:'Escrow released', value:money(atlas.total_escrow_released_usd || 0, 'USD') },
        ]), '')}
        ${panel('Certification threshold', 'SEAL™', listTemplate(certifications.slice(0,4), c => row(c.project_uid, `${fmt(c.type)} • SHI ${fmt(c.shi_composite)}`, c.status, `<button class="btn btn-sm btn-ghost" data-verify-seal="${c.project_uid}">Verify</button>`), 'No certifications yet.'), '')}
      </div>
    </div>`;
  bindDynamicActions();
}

function renderIdent(){
  const professionals = itemsOf(state.datasets.professionals);
  setHero('Permanent professional identity with portable accountability.', 'IDENT™ binds role, band, discipline, SHI history, and accountability into one durable institutional record.', [`${safeCount(professionals)} professionals`, `${num(professionals.filter(p => p.band === 'HONOR').length)} HONOR`, `${num(professionals.filter(p => p.active).length)} active`]);
  setKpis([
    { label:'Professionals', value:num(professionals.length) },
    { label:'Honor band', value:num(professionals.filter(p => p.band === 'HONOR').length) },
    { label:'Trusted band', value:num(professionals.filter(p => p.band === 'TRUSTED').length) },
    { label:'Average PRI', value:avg(professionals.map(p => p.pri_score)) }
  ]);
  el.workspace.innerHTML = panel('IDENT™ registry', 'Professional accountability', table(
    ['Name','Role','Band','Discipline','Country','PRI'],
    professionals.map(p => `<tr><td>${p.name}<div class="muted small">${p.email}</div></td><td>${fmt(p.role)}</td><td>${badge(p.band)}</td><td>${fmt(p.discipline)}</td><td>${fmt(p.country)}</td><td>${fmt(p.pri_score)}</td></tr>`)
  ), '');
}

function renderProjects(){
  const projects = itemsOf(state.datasets.projects);
  const components = itemsOf(state.datasets.components);
  setHero('Immutable project truth from registration to certification.', 'Projects now operate as live TWIN™ records. Open any project to inspect its components, lifecycle events, payments, and public certification posture.', [`${safeCount(projects)} projects`, `${safeCount(components)} components`, `${num(projects.filter(p => p.status === 'active').length)} active`]);
  setKpis([
    { label:'Projects', value:num(projects.length) },
    { label:'Components', value:num(components.length) },
    { label:'Active SHI avg', value:avg(projects.filter(p => p.status === 'active').map(p => p.shi)) },
    { label:'Milestones', value:num(safeCount(state.datasets.milestones)) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Project register', 'TWIN™ projects', table(
        ['Project','Client','Country','Progress','Status'],
        projects.map(p => `<tr><td><button class="link-btn" data-project-detail="${p.uid}">${p.name}</button><div class="muted small code">${p.uid}</div></td><td>${fmt(p.client)}</td><td>${fmt(p.country)}</td><td>${fmt(p.progress)}%</td><td>${badge(p.status)}</td></tr>`)
      ), `<button class="btn btn-sm" data-open-create="project">New project</button>` )}</div>
      <div>${panel('Execution surface', 'Components', listTemplate(components.slice(0,8), c => row(c.uid, `${fmt(c.type)} • ${fmt(c.spec || c.spec_code)} • ${fmt(c.project_uid)}`, c.status, `<button class="btn btn-sm btn-ghost" data-component-detail="${c.uid}">Open</button>`), 'No components yet.'), `<button class="btn btn-sm" data-open-create="component">New component</button>` )}</div>
    </div>`;
  bindDynamicActions();
}

function renderBuild(){
  const evidence = itemsOf(state.datasets.evidence);
  setHero('No evidence, no irreversible action.', 'BUILD™ is now live against the backend upload pipeline. Evidence submissions, approval state, and execution blocks are visible from one place.', [`${safeCount(evidence)} evidence records`, `${num(evidence.filter(e => e.status === 'approved').length)} approved`]);
  setKpis([
    { label:'Evidence items', value:num(evidence.length) },
    { label:'Approved', value:num(evidence.filter(e => e.status === 'approved').length) },
    { label:'Pending', value:num(evidence.filter(e => e.status !== 'approved').length) },
    { label:'Components blocked', value:num(itemsOf(state.datasets.components).filter(c => c.blocked_for_execution).length) }
  ]);
  el.workspace.innerHTML = `
    ${panel('BUILD™ evidence register', 'Evidence-first execution', table(
      ['Component','Type','Status','Submitted','Description'],
      evidence.map(ev => `<tr><td>${fmt(ev.component_uid)}</td><td>${fmt(ev.type)}</td><td>${badge(ev.status)}</td><td>${dateTimeFmt(ev.created_at || ev.timestamp)}</td><td>${fmt(ev.description)}</td></tr>`)
    ), `<button class="btn btn-sm" data-open-create="evidence">Upload evidence</button>`)}
  `;
  bindDynamicActions();
}

function renderVision(){
  const inspections = itemsOf(state.datasets.inspections);
  setHero('Human judgment primary. AI supportive. SHI permanent.', 'VISION™ computes and records SHI-backed inspection truth in the live backend. The frontend now writes real inspection assessments.', [`${safeCount(inspections)} inspections`, `${avg(inspections.map(i => i.shi))} average SHI`]);
  setKpis([
    { label:'Inspections', value:num(inspections.length) },
    { label:'Average SHI', value:avg(inspections.map(i => i.shi)) },
    { label:'Passed', value:num(inspections.filter(i => i.status === 'passed').length) },
    { label:'AI flags', value:num(sum(inspections.map(i => i.ai_flags || 0))) }
  ]);
  el.workspace.innerHTML = panel('SHI inspection ledger', 'VISION™', table(
    ['Component','SHI','Inspector','Status','Reason'],
    inspections.map(i => `<tr><td>${fmt(i.component_uid)}</td><td>${fmt(i.shi)}</td><td>${fmt(i.inspector_id)}</td><td>${badge(i.status)}</td><td>${fmt(i.reason_tag)}</td></tr>`)
  ), `<button class="btn btn-sm" data-open-create="inspection">Record inspection</button>`);
  bindDynamicActions();
}

function renderPay(){
  const milestones = itemsOf(state.datasets.milestones);
  const payments = itemsOf(state.datasets.payments);
  setHero('Money follows structural truth.', 'PAY™ now shows live milestone gates and release records from the backend rather than a frontend-only mock.', [`${safeCount(milestones)} milestones`, `${safeCount(payments)} payments`, `${money(sum(payments.map(p => p.amount || 0)), 'USD')} released`]);
  setKpis([
    { label:'Milestones', value:num(milestones.length) },
    { label:'Released', value:num(milestones.filter(m => m.status === 'released').length) },
    { label:'Payments', value:num(payments.length) },
    { label:'Escrow released', value:money(sum(payments.map(p => p.amount || 0)), 'USD') }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Milestone gate register', 'PAY™', table(
        ['Project','Phase','Required SHI','Amount','Status'],
        milestones.map(m => `<tr><td>${fmt(m.project_uid)}</td><td>${fmt(m.name)}</td><td>${fmt(m.required_shi)}</td><td>${money(m.amount, m.currency)}</td><td>${badge(m.status)}</td></tr>`)
      ), '')}</div>
      <div>${panel('Released payment trail', 'Escrow output', listTemplate(payments.slice(0,10), p => row(p.tx_id || `Payment ${p.id}`, `${money(p.amount, p.currency)} • ${fmt(p.project_uid)} • ${dateFmt(p.date)}`, p.status), 'No payments found.'), '')}</div>
    </div>`;
}

function renderSeal(){
  const certs = itemsOf(state.datasets.certifications);
  setHero('Physical certification with public verifiability.', 'SEAL™ certification records are live, and public certificate verification is now accessible directly from the main frontend.', [`${safeCount(certs)} certifications`, `${num(certs.filter(c => c.status === 'pending_ceremony').length)} pending ceremony`]);
  setKpis([
    { label:'Certifications', value:num(certs.length) },
    { label:'Average certified SHI', value:avg(certs.map(c => c.shi_composite)) },
    { label:'Pending ceremony', value:num(certs.filter(c => c.status === 'pending_ceremony').length) },
    { label:'Issued/ready', value:num(certs.filter(c => ['issued','pending_ceremony'].includes(c.status)).length) }
  ]);
  el.workspace.innerHTML = panel('Certification ledger', 'SEAL™', listTemplate(certs, c => row(c.project_uid, `${fmt(c.type)} • Plate ${fmt(c.physical_plate)} • SHI ${fmt(c.shi_composite)}`, c.status, `<button class="btn btn-sm btn-ghost" data-verify-seal="${c.project_uid}">Verify public record</button>`), 'No certifications available.'), '');
  bindDynamicActions();
}

function renderMarket(){
  const tenders = itemsOf(state.datasets.tenders);
  setHero('Evidence-based procurement, not lowest-bid theatre.', 'MARKET™ surfaces tender opportunities tied to institutional integrity posture.', [`${safeCount(tenders)} tenders`, `${num(tenders.filter(t => t.status === 'open').length)} open`]);
  setKpis([
    { label:'Tenders', value:num(tenders.length) },
    { label:'Open', value:num(tenders.filter(t => t.status === 'open').length) },
    { label:'Pipeline value', value:money(sum(tenders.map(t => t.value || 0)), 'USD') },
    { label:'Closing soon', value:num(tenders.filter(t => t.deadline && new Date(t.deadline) <= addDays(21)).length) }
  ]);
  el.workspace.innerHTML = panel('Tender board', 'MARKET™', table(
    ['Tender','Country','Client','Deadline','Status'],
    tenders.map(t => `<tr><td>${t.name}<div class="muted small code">${t.uid}</div></td><td>${fmt(t.country)}</td><td>${fmt(t.client)}</td><td>${dateFmt(t.deadline)}</td><td>${badge(t.status)}</td></tr>`)
  ), `<button class="btn btn-sm" data-open-create="tender">Publish tender</button>`);
  bindDynamicActions();
}

function renderOrigin(){
  const materials = itemsOf(state.datasets.materials);
  setHero('Materials become permanent evidence, not temporary claims.', 'ORIGIN™ tracks batches, verification state, and supplier traceability inside the live backend.', [`${safeCount(materials)} material batches`, `${num(materials.filter(m => m.verified).length)} verified`]);
  setKpis([
    { label:'Batches', value:num(materials.length) },
    { label:'Verified', value:num(materials.filter(m => m.verified).length) },
    { label:'Suspended', value:num(materials.filter(m => m.status === 'suspended').length) },
    { label:'Projects covered', value:num(new Set(materials.flatMap(m => m.projects_used || [])).size) }
  ]);
  el.workspace.innerHTML = panel('Material traceability ledger', 'ORIGIN™', table(
    ['Batch','Supplier','Grade','Strength','Status'],
    materials.map(m => `<tr><td>${fmt(m.batch_uid || m.name)}</td><td>${fmt(m.supplier)}</td><td>${fmt(m.grade)}</td><td>${fmt(m.test_strength)} / ${fmt(m.required_strength)}</td><td>${badge(m.status)}</td></tr>`)
  ), '');
}

function renderMonitor(){
  const sensors = itemsOf(state.datasets.sensors);
  const alerts = itemsOf(state.datasets.alerts);
  setHero('The record does not end at construction handover.', 'MONITOR™ combines live sensors and alerting for post-construction visibility.', [`${safeCount(sensors)} sensors`, `${safeCount(alerts)} alerts`]);
  setKpis([
    { label:'Sensors', value:num(sensors.length) },
    { label:'Alerts', value:num(alerts.length) },
    { label:'Normal status', value:num(sensors.filter(s => s.status === 'normal').length) },
    { label:'Threshold breaches', value:num(alerts.filter(a => a.status !== 'resolved').length) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Sensor register', 'MONITOR™', table(
        ['Component','Type','Reading','Threshold','Status'],
        sensors.map(s => `<tr><td>${fmt(s.component_uid)}</td><td>${fmt(s.type)}</td><td>${fmt(s.current_reading)} ${fmt(s.unit)}</td><td>${fmt(s.threshold)} ${fmt(s.unit)}</td><td>${badge(s.status)}</td></tr>`)
      ), '')}</div>
      <div>${panel('Operational alerts', 'Threshold intelligence', listTemplate(alerts, a => row(a.type || `Alert ${a.id}`, a.message || a.description || '', a.status), 'No alerts available.'), '')}</div>
    </div>`;
}

function renderLex(){
  const disputes = itemsOf(state.datasets.disputes);
  setHero('Disputes resolve from records, not memory.', 'LEX™ remains evidence-first: dispute records, status, and resolutions are pulled from the backend.', [`${safeCount(disputes)} disputes`, `${num(disputes.filter(d => d.status === 'resolved').length)} resolved`]);
  setKpis([
    { label:'Disputes', value:num(disputes.length) },
    { label:'Resolved', value:num(disputes.filter(d => d.status === 'resolved').length) },
    { label:'Open/review', value:num(disputes.filter(d => d.status !== 'resolved').length) },
    { label:'Projects touched', value:num(new Set(disputes.map(d => d.project_uid)).size) }
  ]);
  el.workspace.innerHTML = panel('Dispute register', 'LEX™', listTemplate(disputes, d => row(d.uid || `Dispute ${d.id}`, `${fmt(d.project_uid)} • ${fmt(d.description)}${d.resolution ? `<br><span class="muted">Resolution: ${d.resolution}</span>` : ''}`, d.status), 'No disputes available.'), '');
}

function renderAtlas(){
  const atlas = state.datasets.atlas || {};
  const reports = itemsOf(state.datasets.atlasReports);
  setHero('National and portfolio intelligence from project truth.', 'ATLAS™ now reads live portfolio output and published reports from the institutional backend.', [`${num(atlas.countries_active)} countries active`, `${safeCount(reports)} published reports`]);
  setKpis([
    { label:'Countries active', value:num(atlas.countries_active) },
    { label:'Projects monitored', value:num(atlas.projects_monitored) },
    { label:'Avg SHI', value:fmt(atlas.avg_shi) },
    { label:'Escrow released', value:money(atlas.total_escrow_released_usd || 0, 'USD') }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Portfolio intelligence summary', 'ATLAS™', cardStats([
        { label:'Certified projects', value:num(atlas.certified_projects) },
        { label:'Alerts open', value:num(atlas.alerts_open) },
        { label:'Disputes open', value:num(atlas.disputes_open) },
        { label:'Tenders open', value:num(atlas.open_tenders) },
      ]), '')}</div>
      <div>${panel('Published reports', 'ATLAS™ reports', listTemplate(reports, r => row(r.title || r.report_type, `${fmt(r.country_scope)} • ${fmt(r.period_label)}`, r.status), 'No reports yet.'), `<button class="btn btn-sm" data-open-create="report">Publish report</button>` )}</div>
    </div>`;
  bindDynamicActions();
}

function renderVerifund(){
  const products = itemsOf(state.datasets.verifundProducts);
  const apps = itemsOf(state.datasets.verifundApps);
  setHero('Finance and insurance should price truth, not paper claims.', 'VERIFUND™ is now live in the frontend for products, applications, and underwriting evaluation actions.', [`${safeCount(products)} products`, `${safeCount(apps)} applications`]);
  setKpis([
    { label:'Products', value:num(products.length) },
    { label:'Applications', value:num(apps.length) },
    { label:'Submitted', value:num(apps.filter(a => a.status === 'submitted').length) },
    { label:'Requested capital', value:money(sum(apps.map(a => a.requested_amount || 0)), 'USD') }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Financial products', 'VERIFUND™', listTemplate(products, p => row(p.code || p.name, `${fmt(p.category)} • base ${fmt(p.base_rate_bps)} bps • min SHI ${fmt(p.min_shi)}`, p.active ? 'active' : 'inactive'), 'No products available.'), `<button class="btn btn-sm" data-open-create="product">Create product</button>` )}</div>
      <div>${panel('Underwriting applications', 'Risk pipeline', listTemplate(apps, a => row(a.application_uid || `Application ${a.id}`, `${fmt(a.project_uid)} • ${money(a.requested_amount, a.currency)} • ${fmt(a.product_code)}`, a.status, `<button class="btn btn-sm btn-ghost" data-evaluate-app="${a.id}">Evaluate</button>`), 'No applications yet.'), `<button class="btn btn-sm" data-open-create="application">New application</button>` )}</div>
    </div>`;
  bindDynamicActions();
}

function renderAcademy(){
  const paths = itemsOf(state.datasets.academyPaths);
  const courses = itemsOf(state.datasets.academyCourses);
  const credentials = itemsOf(state.datasets.academyCredentials);
  const advancement = state.datasets.academyAdvancement || {};
  setHero('Band progression must be earned through demonstrated evidence.', 'ACADEMY™ is now backed by the real course, path, enrollment, and credential APIs.', [`${safeCount(paths)} paths`, `${safeCount(courses)} courses`, `${safeCount(credentials)} credentials`]);
  setKpis([
    { label:'Current band', value:fmt(advancement.current_band) },
    { label:'Eligible next band', value:fmt(advancement.eligible_next_band) },
    { label:'Courses complete', value:num(advancement.completed_courses_count) },
    { label:'Paths available', value:num(paths.length) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Learning paths', 'ACADEMY™', listTemplate(paths, p => row(p.code || p.title, `${fmt(p.target_band)} • ${fmt(p.discipline_scope)} • ${fmt(p.description)}`, p.status || 'active'), 'No paths available.'), `<button class="btn btn-sm" data-open-create="path">Create path</button>` )}
        ${panel('Credentials awarded', 'Professional advancement', listTemplate(credentials, c => row(c.title || c.code || `Credential ${c.id}`, `${dateFmt(c.issued_at)} • ${fmt(c.path_code || c.code)}`, c.status || 'awarded'), 'No credentials awarded.'), '')}
      </div>
      <div>${panel('Course catalogue', 'ACADEMY™', listTemplate(courses, c => row(c.code || c.title, `${fmt(c.path_code)} • ${fmt(c.delivery_mode)} • ${fmt(c.hours)} hours`, c.status || 'active'), 'No courses available.'), `<button class="btn btn-sm" data-open-create="course">Create course</button>` )}</div>
    </div>`;
  bindDynamicActions();
}

function renderClone(){
  const clone = state.datasets.cloneSummary || {};
  setHero('Country expansion is a governed operating system, not a slide deck.', 'CLONE™ now surfaces rollout summary from the backend, connected to governance and regulatory readiness.', [`${num(clone.total_countries)} countries`, `${num(clone.active_tenants)} active tenants`]);
  setKpis([
    { label:'Countries', value:num(clone.total_countries) },
    { label:'Active tenants', value:num(clone.active_tenants) },
    { label:'Launch programs', value:num(clone.launch_programs) },
    { label:'Revenue rules', value:num(clone.revenue_rules) }
  ]);
  el.workspace.innerHTML = panel('Rollout summary', 'CLONE™', `<pre class="note code">${escapeHtml(JSON.stringify(clone, null, 2))}</pre>`, '');
}

function renderGovernance(){
  const dashboard = state.datasets.governanceDashboard || {};
  const members = itemsOf(state.datasets.governanceMembers);
  const resolutions = itemsOf(state.datasets.governanceResolutions);
  setHero('Legitimacy is part of the moat.', 'Governance, CST composition, and resolution state are now visible in the same frontend as operational modules.', [`${safeCount(members)} CST members`, `${safeCount(resolutions)} resolutions`]);
  setKpis([
    { label:'CST members', value:num(dashboard.cst_members || members.length) },
    { label:'Committees', value:num(dashboard.committees) },
    { label:'Open resolutions', value:num(dashboard.open_resolutions) },
    { label:'Delegations', value:num(dashboard.active_delegations) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Council composition', 'Governance', listTemplate(members, m => row(`${fmt(m.professional_id)} • ${fmt(m.appointment_title)}`, `${dateFmt(m.term_start)} • voting ${m.voting_rights ? 'enabled' : 'disabled'}`, m.status), 'No members available.'), '')}</div>
      <div>${panel('Resolutions', 'Governance', listTemplate(resolutions, r => row(r.resolution_uid || r.title, `${fmt(r.title)} • ${fmt(r.committee_code)} • effective ${dateFmt(r.effective_date)}`, r.status), 'No resolutions available.'), '')}</div>
    </div>`;
}

function renderRegulatory(){
  const readiness = state.datasets.regulatoryReadiness || {};
  const regs = itemsOf(state.datasets.regulations);
  const consultations = itemsOf(state.datasets.consultations);
  const mappings = itemsOf(state.datasets.complianceMappings);
  setHero('Regulatory co-creation must be operational, not rhetorical.', 'Regulations, consultations, and compliance mappings are now tied into the frontend experience.', [`${safeCount(regs)} regulations`, `${safeCount(consultations)} consultations`, `${safeCount(mappings)} mappings`]);
  setKpis([
    { label:'Countries tracked', value:num(readiness.countries_tracked) },
    { label:'Draft regulations', value:num(readiness.draft_regulations) },
    { label:'Open consultations', value:num(readiness.open_consultations) },
    { label:'Compliance mappings', value:num(readiness.compliance_mappings) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Regulations', 'Regulatory framework', listTemplate(regs, r => row(r.regulation_code || r.title, `${fmt(r.country_code)} • ${fmt(r.category)} • ${fmt(r.summary)}`, r.status), 'No regulations available.'), '')}
        ${panel('Consultations', 'Regulatory engagement', listTemplate(consultations, c => row(c.consultation_uid || c.title, `${fmt(c.country_code)} • ${fmt(c.consultation_type)} • ${fmt(c.opened_at_label)}`, c.status), 'No consultations available.'), '')}
      </div>
      <div>${panel('Compliance mappings', 'Module-to-standard map', listTemplate(mappings, m => row(`${fmt(m.country_code)} • ${fmt(m.module_code)}`, `${fmt(m.standard_code)} • ${fmt(m.requirement_summary)}`, m.status), 'No mappings available.'), '')}</div>
    </div>`;
}

function renderAudit(){
  const logs = itemsOf(state.datasets.audit);
  setHero('The record is append-only, and the record matters.', 'Audit Trail remains the institutional backbone: authentication, creation, approvals, evaluation, and lifecycle changes are visible from one place.', [`${safeCount(logs)} audit entries`]);
  setKpis([
    { label:'Audit entries', value:num(logs.length) },
    { label:'Most recent actor', value:fmt(logs[0]?.actor) },
    { label:'Most recent action', value:fmt(logs[0]?.action) },
    { label:'Access level', value:fmt(state.currentUser?.role) }
  ]);
  el.workspace.innerHTML = panel('Immutable audit log', 'TWIN™ / Audit', table(
    ['Timestamp','Action','Actor','Detail'],
    logs.map(log => `<tr><td>${dateTimeFmt(log.created_at || log.timestamp)}</td><td class="code">${fmt(log.action)}</td><td>${fmt(log.actor)}</td><td>${fmt(log.detail)}</td></tr>`)
  ), '');
}

function bindDynamicActions(){
  document.querySelectorAll('[data-open-create]').forEach(button => button.addEventListener('click', () => openCreateModal(button.dataset.openCreate)));
  document.querySelectorAll('[data-project-detail]').forEach(button => button.addEventListener('click', () => openProjectDetail(button.dataset.projectDetail)));
  document.querySelectorAll('[data-component-detail]').forEach(button => button.addEventListener('click', () => openComponentDetail(button.dataset.componentDetail)));
  document.querySelectorAll('[data-mark-read]').forEach(button => button.addEventListener('click', () => markNotificationRead(button.dataset.markRead)));
  document.querySelectorAll('[data-verify-seal]').forEach(button => button.addEventListener('click', () => verifySeal(button.dataset.verifySeal)));
  document.querySelectorAll('[data-evaluate-app]').forEach(button => button.addEventListener('click', () => evaluateApplication(button.dataset.evaluateApp)));
}

async function markNotificationRead(id){
  try {
    await request(`/notifications/${id}/read`, { method:'POST' });
    toast('Notification marked as read.', 'success');
    await loadAllData();
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function verifySeal(projectUid){
  try {
    const data = await fetch(`${API_BASE}/public/seal/${encodeURIComponent(projectUid)}`).then(async res => {
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail || 'Unable to verify seal');
      return body;
    });
    openModal('Public SEAL™ verification', 'External public record', `<pre class="note code">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`);
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function evaluateApplication(id){
  try {
    const data = await request(`/verifund/applications/${id}/evaluate`, { method:'POST' });
    openModal('Underwriting evaluation', 'VERIFUND™ decision', `<pre class="note code">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`);
    await loadAllData();
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function openProjectDetail(projectUid){
  const project = itemsOf(state.datasets.projects).find(p => p.uid === projectUid);
  try {
    const events = await request(`/twin/projects/${encodeURIComponent(projectUid)}/events`);
    const components = itemsOf(state.datasets.components).filter(c => c.project_uid === projectUid);
    openModal(
      project?.name || projectUid,
      'TWIN™ project detail',
      `
      <div class="grid-2">
        <div class="card">${cardStats([
          { label:'Project UID', value:fmt(project?.uid) },
          { label:'Country', value:fmt(project?.country) },
          { label:'SHI', value:fmt(project?.shi) },
          { label:'Progress', value:`${fmt(project?.progress)}%` },
        ])}</div>
        <div class="card"><div class="section-title">Description</div><div class="muted">${fmt(project?.description)}</div></div>
      </div>
      <div class="actions-row"><button class="btn btn-sm" data-open-create="component">Add component</button><button class="btn btn-sm btn-ghost" data-open-create="evidence">Upload evidence</button></div>
      <div class="grid-2" style="margin-top:16px;">
        <div>${panel('Component surface', 'Project components', listTemplate(components, c => row(c.uid, `${fmt(c.type)} • ${fmt(c.status)} • ${fmt(c.spec)}`, c.status), 'No components for this project.'), '')}</div>
        <div>${panel('Twin event stream', 'Immutable record', listTemplate(itemsOf(events), ev => row(ev.event_type, `${dateTimeFmt(ev.occurred_at || ev.created_at)} • ${fmt(ev.aggregate_type)} • ${fmt(ev.aggregate_uid)}`, 'recorded'), 'No events recorded yet.'), '')}</div>
      </div>`
    );
    bindDynamicActions();
  } catch (error) {
    toast(error.message, 'error');
  }
}

function openComponentDetail(componentUid){
  const component = itemsOf(state.datasets.components).find(c => c.uid === componentUid);
  const evidence = itemsOf(state.datasets.evidence).filter(e => e.component_uid === componentUid);
  const inspections = itemsOf(state.datasets.inspections).filter(i => i.component_uid === componentUid);
  openModal(componentUid, 'Component detail', `
    <div class="grid-2">
      <div>${panel('Component profile', 'Execution identity', cardStats([
        { label:'Project', value:fmt(component?.project_uid) },
        { label:'Type', value:fmt(component?.type) },
        { label:'Grid', value:fmt(component?.grid) },
        { label:'Status', value:fmt(component?.status) },
      ]), '')}</div>
      <div>${panel('Execution posture', 'BUILD™ / VISION™', listTemplate([
        { title:'Specification', sub: component?.spec },
        { title:'Blocked for execution', sub: String(component?.blocked_for_execution) },
        { title:'Evidence required', sub: String(component?.evidence_required) },
      ], item => row(item.title, item.sub, 'recorded')), '')}</div>
    </div>
    <div class="grid-2" style="margin-top:16px;">
      <div>${panel('Evidence', 'BUILD™', listTemplate(evidence, e => row(e.type || `Evidence ${e.id}`, `${fmt(e.description)} • ${dateTimeFmt(e.created_at || e.timestamp)}`, e.status), 'No evidence yet.'), '')}</div>
      <div>${panel('Inspections', 'VISION™', listTemplate(inspections, i => row(`SHI ${fmt(i.shi)}`, `${fmt(i.reason_tag)} • ${dateTimeFmt(i.created_at || i.timestamp)}`, i.status), 'No inspections yet.'), '')}</div>
    </div>
  `);
}

function openQuickCreateModal(){
  openModal('Quick create', 'Institutional actions', `
    <div class="list">${quickCreateOptions.map(option => `<div class="list-item"><div class="list-item-top"><div><div class="list-item-title">${option.label}</div><div class="list-item-sub">Open a live backend creation form.</div></div><button class="btn btn-sm" data-open-create="${option.key}">Open</button></div></div>`).join('')}</div>
  `);
  bindDynamicActions();
}

function openCreateModal(kind){
  const forms = {
    project: projectForm,
    component: componentForm,
    evidence: evidenceForm,
    inspection: inspectionForm,
    tender: tenderForm,
    report: reportForm,
    product: productForm,
    application: applicationForm,
    path: pathForm,
    course: courseForm,
  };
  const renderer = forms[kind];
  if (!renderer) return toast('Form not configured.', 'error');
  const config = renderer();
  openModal(config.title, config.eyebrow, config.body);
  const form = document.getElementById(config.formId);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      await config.submit(new FormData(form));
      closeModal();
      await loadAllData();
    } catch (error) {
      toast(error.message, 'error');
    }
  });
}

function projectForm(){
  return {
    title:'Create project', eyebrow:'Projects / TWIN™', formId:'projectCreateForm', body:`
      <form id="projectCreateForm" class="form-grid two">
        <label><span>UID</span><input name="uid" required /></label>
        <label><span>Name</span><input name="name" required /></label>
        <label><span>Client</span><input name="client" required /></label>
        <label><span>Country</span><input name="country" required /></label>
        <label><span>Type</span><input name="type" value="Infrastructure" required /></label>
        <label><span>Currency</span><input name="currency" value="USD" required /></label>
        <label><span>Value</span><input name="value" type="number" min="0" required /></label>
        <label><span>Phase</span><input name="phase" value="Foundation & Substructure" required /></label>
        <label><span>Status</span><input name="status" value="active" required /></label>
        <label><span>Progress</span><input name="progress" type="number" min="0" max="100" value="0" required /></label>
        <label><span>Started</span><input name="started" type="date" /></label>
        <label><span>Target completion</span><input name="target_completion" type="date" /></label>
        <label style="grid-column:1/-1"><span>Description</span><textarea name="description" rows="4"></textarea></label>
        <button class="btn btn-primary" type="submit">Create project</button>
      </form>`,
    submit: async (fd) => {
      await request('/projects', { method:'POST', body: JSON.stringify({
        uid: fd.get('uid'), name: fd.get('name'), client: fd.get('client'), country: fd.get('country'), type: fd.get('type'), value: Number(fd.get('value')), currency: fd.get('currency'), phase: fd.get('phase'), status: fd.get('status'), progress: Number(fd.get('progress')), started: fd.get('started') || null, target_completion: fd.get('target_completion') || null, description: fd.get('description') || null
      })});
      toast('Project created.', 'success');
    }
  };
}

function componentForm(){
  const projectOptions = itemsOf(state.datasets.projects).map(p => `<option value="${p.uid}">${p.uid} — ${p.name}</option>`).join('');
  return {
    title:'Create component', eyebrow:'Execution surface', formId:'componentCreateForm', body:`
      <form id="componentCreateForm" class="form-grid two">
        <label><span>UID</span><input name="uid" required /></label>
        <label><span>Project</span><select name="project_uid" required>${projectOptions}</select></label>
        <label><span>Type</span><input name="type" value="Column" required /></label>
        <label><span>Specification</span><input name="spec" required /></label>
        <label><span>Level</span><input name="level" /></label>
        <label><span>Grid</span><input name="grid" /></label>
        <label><span>Status</span><input name="status" value="pending" /></label>
        <label><span>Evidence required</span><select name="evidence_required"><option value="true">true</option><option value="false">false</option></select></label>
        <label><span>Blocked for execution</span><select name="blocked_for_execution"><option value="true">true</option><option value="false">false</option></select></label>
        <label style="grid-column:1/-1"><span>Notes</span><textarea name="notes" rows="3"></textarea></label>
        <button class="btn btn-primary" type="submit">Create component</button>
      </form>`,
    submit: async (fd) => {
      await request('/components', { method:'POST', body: JSON.stringify({
        uid: fd.get('uid'), project_uid: fd.get('project_uid'), type: fd.get('type'), spec: fd.get('spec'), level: fd.get('level') || null, grid: fd.get('grid') || null, status: fd.get('status') || null, evidence_required: fd.get('evidence_required') === 'true', blocked_for_execution: fd.get('blocked_for_execution') === 'true', notes: fd.get('notes') || null
      })});
      toast('Component created.', 'success');
    }
  };
}

function evidenceForm(){
  const componentOptions = itemsOf(state.datasets.components).map(c => `<option value="${c.uid}">${c.uid}</option>`).join('');
  return {
    title:'Upload evidence', eyebrow:'BUILD™ live upload', formId:'evidenceCreateForm', body:`
      <div class="note">This form writes to the real multipart evidence endpoint.</div>
      <form id="evidenceCreateForm" class="form-grid one" style="margin-top:14px;">
        <label><span>Component</span><select name="component_uid" required>${componentOptions}</select></label>
        <label><span>Type</span><input name="type" value="CAPTURE-LARGE" /></label>
        <label><span>Description</span><textarea name="description" rows="3"></textarea></label>
        <label><span>File</span><input name="file" type="file" required /></label>
        <button class="btn btn-primary" type="submit">Upload evidence</button>
      </form>`,
    submit: async (fd) => {
      await request('/evidence/upload', { method:'POST', body: fd });
      toast('Evidence uploaded.', 'success');
    }
  };
}

function inspectionForm(){
  const componentOptions = itemsOf(state.datasets.components).filter(c => !c.blocked_for_execution).map(c => `<option value="${c.uid}">${c.uid}</option>`).join('');
  return {
    title:'Record inspection', eyebrow:'VISION™ write path', formId:'inspectionCreateForm', body:`
      <div class="note">Only components not blocked for execution can be inspected through this route.</div>
      <form id="inspectionCreateForm" class="form-grid two" style="margin-top:14px;">
        <label><span>Component</span><select name="component_uid" required>${componentOptions}</select></label>
        <label><span>AI flags</span><input name="ai_flags" type="number" value="0" min="0" /></label>
        <label><span>Material score</span><input name="material_score" type="number" value="90" min="0" max="100" required /></label>
        <label><span>Assembly score</span><input name="assembly_score" type="number" value="90" min="0" max="100" required /></label>
        <label><span>Environmental score</span><input name="env_score" type="number" value="90" min="0" max="100" required /></label>
        <label><span>Supervision score</span><input name="supervision_score" type="number" value="90" min="0" max="100" required /></label>
        <label style="grid-column:1/-1"><span>Reason tag</span><textarea name="reason_tag" rows="3" required></textarea></label>
        <button class="btn btn-primary" type="submit">Create inspection</button>
      </form>`,
    submit: async (fd) => {
      await request('/vision/inspections', { method:'POST', body: JSON.stringify({
        component_uid: fd.get('component_uid'), material_score:Number(fd.get('material_score')), assembly_score:Number(fd.get('assembly_score')), env_score:Number(fd.get('env_score')), supervision_score:Number(fd.get('supervision_score')), ai_flags:Number(fd.get('ai_flags') || 0), reason_tag: fd.get('reason_tag')
      })});
      toast('Inspection recorded.', 'success');
    }
  };
}

function tenderForm(){
  return {
    title:'Publish tender', eyebrow:'MARKET™', formId:'tenderCreateForm', body:`
      <form id="tenderCreateForm" class="form-grid two">
        <label><span>UID</span><input name="uid" required /></label>
        <label><span>Name</span><input name="name" required /></label>
        <label><span>Client</span><input name="client" required /></label>
        <label><span>Country</span><input name="country" required /></label>
        <label><span>Value</span><input name="value" type="number" required /></label>
        <label><span>Currency</span><input name="currency" value="USD" required /></label>
        <label><span>Deadline</span><input name="deadline" type="date" /></label>
        <label><span>Status</span><input name="status" value="open" required /></label>
        <label><span>Type</span><input name="type" value="Infrastructure" required /></label>
        <label style="grid-column:1/-1"><span>Description</span><textarea name="description" rows="3"></textarea></label>
        <button class="btn btn-primary" type="submit">Publish tender</button>
      </form>`,
    submit: async (fd) => {
      await request('/tenders', { method:'POST', body: JSON.stringify({
        uid:fd.get('uid'), name:fd.get('name'), client:fd.get('client'), country:fd.get('country'), value:Number(fd.get('value')), currency:fd.get('currency'), deadline:fd.get('deadline') || null, status:fd.get('status'), type:fd.get('type'), description:fd.get('description') || null
      })});
      toast('Tender published.', 'success');
    }
  };
}

function reportForm(){
  return {
    title:'Publish ATLAS report', eyebrow:'ATLAS™', formId:'reportCreateForm', body:`
      <form id="reportCreateForm" class="form-grid two">
        <label><span>Title</span><input name="title" required /></label>
        <label><span>Country scope</span><input name="country_scope" value="Multi-country" /></label>
        <label><span>Report type</span><input name="report_type" value="portfolio" /></label>
        <label><span>Period label</span><input name="period_label" value="Q2-2026" /></label>
        <button class="btn btn-primary" type="submit">Publish report</button>
      </form>`,
    submit: async (fd) => {
      await request('/atlas/reports', { method:'POST', body: JSON.stringify({
        title:fd.get('title'), country_scope:fd.get('country_scope') || null, report_type:fd.get('report_type'), period_label:fd.get('period_label') || null
      })});
      toast('ATLAS report published.', 'success');
    }
  };
}

function productForm(){
  return {
    title:'Create VERIFUND product', eyebrow:'VERIFUND™', formId:'productCreateForm', body:`
      <form id="productCreateForm" class="form-grid two">
        <label><span>Code</span><input name="code" required /></label>
        <label><span>Name</span><input name="name" required /></label>
        <label><span>Category</span><input name="category" value="insurance" required /></label>
        <label><span>Base rate (bps)</span><input name="base_rate_bps" type="number" value="100" required /></label>
        <label><span>Minimum SHI</span><input name="min_shi" type="number" value="82" /></label>
        <label><span>Active</span><select name="active"><option value="true">true</option><option value="false">false</option></select></label>
        <label style="grid-column:1/-1"><span>Description</span><textarea name="description" rows="3"></textarea></label>
        <button class="btn btn-primary" type="submit">Create product</button>
      </form>`,
    submit: async (fd) => {
      await request('/verifund/products', { method:'POST', body: JSON.stringify({
        code:fd.get('code'), name:fd.get('name'), category:fd.get('category'), description:fd.get('description') || null, base_rate_bps:Number(fd.get('base_rate_bps')), min_shi: Number(fd.get('min_shi') || 0), active: fd.get('active') === 'true'
      })});
      toast('VERIFUND product created.', 'success');
    }
  };
}

function applicationForm(){
  const projectOptions = itemsOf(state.datasets.projects).map(p => `<option value="${p.uid}">${p.uid}</option>`).join('');
  const productOptions = itemsOf(state.datasets.verifundProducts).map(p => `<option value="${p.code}">${p.code}</option>`).join('');
  return {
    title:'Create underwriting application', eyebrow:'VERIFUND™', formId:'applicationCreateForm', body:`
      <form id="applicationCreateForm" class="form-grid two">
        <label><span>Application UID</span><input name="application_uid" required /></label>
        <label><span>Project</span><select name="project_uid" required>${projectOptions}</select></label>
        <label><span>Product</span><select name="product_code" required>${productOptions}</select></label>
        <label><span>Applicant name</span><input name="applicant_name" required /></label>
        <label><span>Requested amount</span><input name="requested_amount" type="number" required /></label>
        <label><span>Currency</span><input name="currency" value="USD" required /></label>
        <button class="btn btn-primary" type="submit">Create application</button>
      </form>`,
    submit: async (fd) => {
      await request('/verifund/applications', { method:'POST', body: JSON.stringify({
        application_uid:fd.get('application_uid'), project_uid:fd.get('project_uid'), product_code:fd.get('product_code'), applicant_name:fd.get('applicant_name'), requested_amount:Number(fd.get('requested_amount')), currency:fd.get('currency')
      })});
      toast('Underwriting application created.', 'success');
    }
  };
}

function pathForm(){
  return {
    title:'Create learning path', eyebrow:'ACADEMY™', formId:'pathCreateForm', body:`
      <form id="pathCreateForm" class="form-grid two">
        <label><span>Code</span><input name="code" required /></label>
        <label><span>Title</span><input name="title" required /></label>
        <label><span>Target band</span><input name="target_band" value="TRUSTED" required /></label>
        <label><span>Discipline scope</span><input name="discipline_scope" value="Structural Engineering" /></label>
        <label style="grid-column:1/-1"><span>Description</span><textarea name="description" rows="3"></textarea></label>
        <button class="btn btn-primary" type="submit">Create path</button>
      </form>`,
    submit: async (fd) => {
      await request('/academy/paths', { method:'POST', body: JSON.stringify({
        code:fd.get('code'), title:fd.get('title'), target_band:fd.get('target_band'), discipline_scope:fd.get('discipline_scope') || null, description:fd.get('description') || null
      })});
      toast('Learning path created.', 'success');
    }
  };
}

function courseForm(){
  const pathOptions = itemsOf(state.datasets.academyPaths).map(p => `<option value="${p.code}">${p.code}</option>`).join('');
  return {
    title:'Create course', eyebrow:'ACADEMY™', formId:'courseCreateForm', body:`
      <form id="courseCreateForm" class="form-grid two">
        <label><span>Path code</span><select name="path_code" required>${pathOptions}</select></label>
        <label><span>Course code</span><input name="code" required /></label>
        <label><span>Title</span><input name="title" required /></label>
        <label><span>Delivery mode</span><input name="delivery_mode" value="async" /></label>
        <label><span>Hours</span><input name="hours" type="number" value="4" /></label>
        <label style="grid-column:1/-1"><span>Description</span><textarea name="description" rows="3"></textarea></label>
        <button class="btn btn-primary" type="submit">Create course</button>
      </form>`,
    submit: async (fd) => {
      await request('/academy/courses', { method:'POST', body: JSON.stringify({
        path_code:fd.get('path_code'), code:fd.get('code'), title:fd.get('title'), delivery_mode:fd.get('delivery_mode') || null, hours:Number(fd.get('hours') || 0), description:fd.get('description') || null
      })});
      toast('Course created.', 'success');
    }
  };
}

function openModal(title, eyebrow, body){
  el.modalTitle.textContent = title;
  el.modalEyebrow.textContent = eyebrow;
  el.modalBody.innerHTML = body;
  el.modal.classList.add('open');
}
function closeModal(){ el.modal.classList.remove('open'); }

function avg(values){
  const clean = values.filter(v => typeof v === 'number' && !Number.isNaN(v));
  if (!clean.length) return '—';
  return (clean.reduce((a,b) => a+b, 0) / clean.length).toFixed(1);
}
function sum(values){ return values.reduce((a,b) => a + (Number(b) || 0), 0); }
function addDays(days){ const d = new Date(); d.setDate(d.getDate()+days); return d; }
function escapeHtml(input){
  return String(input)
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#39;');
}

async function init(){
  bind();
  if (token()) await bootstrapApp();
}

init();


// ===== Enterprise UI completion pass overrides =====
quickCreateOptions.push(
  { key: 'atlas_subscription', label: 'Create ATLAS subscription' },
  { key: 'member', label: 'Appoint CST member' },
  { key: 'committee', label: 'Create committee' },
  { key: 'resolution', label: 'Draft resolution' },
  { key: 'vote', label: 'Cast governance vote' },
  { key: 'country', label: 'Add country rollout' },
  { key: 'tenant', label: 'Create country tenant' },
  { key: 'launch_program', label: 'Create launch program' },
  { key: 'revenue_rule', label: 'Create revenue rule' },
  { key: 'regulation', label: 'Create regulation' },
  { key: 'consultation', label: 'Open consultation' },
  { key: 'mapping', label: 'Add compliance mapping' },
  { key: 'dispute', label: 'Open dispute' },
  { key: 'material', label: 'Register material batch' },
  { key: 'sensor_reading', label: 'Capture sensor reading' },
  { key: 'enrollment', label: 'Enroll in course' },
  { key: 'complete_enrollment', label: 'Complete enrollment' },
  { key: 'issue_seal', label: 'Issue certification' },
  { key: 'atlas_subscription', label: 'Create ATLAS subscription' },
  { key: 'feature_flag', label: 'Set feature flag' },
  { key: 'country_config', label: 'Set country config' },
  { key: 'policy_rule', label: 'Create policy rule' },
  { key: 'policy_eval', label: 'Evaluate policy access' },
  { key: 'workflow_definition', label: 'Create workflow definition' },
  { key: 'workflow_state', label: 'Create workflow state' },
  { key: 'workflow_transition', label: 'Create workflow transition' },
  { key: 'workflow_instance', label: 'Create workflow instance' },
  { key: 'workflow_action', label: 'Execute workflow action' }
);

async function loadAllData(){
  try {
    const endpoints = {
      summary: '/dashboard/summary',
      professionals: '/professionals',
      projects: '/projects',
      components: '/components',
      evidence: '/evidence',
      inspections: '/vision/inspections',
      milestones: '/pay/milestones',
      payments: '/pay/payments',
      tenders: '/tenders',
      materials: '/materials',
      certifications: '/seal/certifications',
      sensors: '/monitor/sensors',
      alerts: '/monitor/alerts',
      disputes: '/lex/disputes',
      atlas: '/atlas/portfolio/overview',
      atlasSubscriptions: '/atlas/subscriptions',
      atlasReports: '/atlas/reports',
      verifundProducts: '/verifund/products',
      verifundApps: '/verifund/applications',
      academyPaths: '/academy/paths',
      academyCourses: '/academy/courses',
      academyEnrollments: '/academy/enrollments',
      academyCredentials: '/academy/credentials',
      academyAdvancement: '/academy/advancement/me',
      cloneSummary: '/clone/rollout/summary',
      cloneCountries: '/clone/countries',
      cloneTenants: '/clone/tenants',
      cloneLaunchPrograms: '/clone/launch-programs',
      cloneRevenueRules: '/clone/revenue-share-rules',
      governanceDashboard: '/governance/dashboard',
      governanceMembers: '/governance/members',
      governanceCommittees: '/governance/committees',
      governanceResolutions: '/governance/resolutions',
      regulatoryReadiness: '/regulatory/readiness',
      regulations: '/regulatory/regulations',
      consultations: '/regulatory/consultations',
      complianceMappings: '/regulatory/compliance-mappings',
      notifications: '/notifications',
      audit: '/audit'
    };
    const entries = await Promise.all(Object.entries(endpoints).map(async ([key, path]) => {
      try { return [key, await request(path)]; }
      catch (error) { return [key, { __error: error.message }]; }
    }));
    state.datasets = Object.fromEntries(entries);
    state.summary = state.datasets.summary?.__error ? null : state.datasets.summary;
    renderNav();
    renderView();
    toast('Platform data refreshed.', 'success');
  } catch (error) {
    toast(`Refresh failed: ${error.message}`, 'error');
  }
}

function renderAtlas(){
  const atlas = state.datasets.atlas || {};
  const subs = itemsOf(state.datasets.atlasSubscriptions);
  const reports = itemsOf(state.datasets.atlasReports);
  setHero('National and portfolio intelligence from project truth.', 'ATLAS™ now combines live portfolio analytics, report publishing, and subscription management for governments, insurers, DFIs, and portfolio owners.', [`${num(atlas.total_projects)} total projects`, `${safeCount(reports)} reports`, `${safeCount(subs)} subscribers`]);
  setKpis([
    { label:'Projects monitored', value:num(atlas.total_projects) },
    { label:'Active projects', value:num(atlas.active_projects) },
    { label:'Average SHI', value:fmt(atlas.avg_shi) },
    { label:'Escrow released', value:money(atlas.payment_released_total || 0, 'USD') }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Portfolio intelligence summary', 'ATLAS™', cardStats([
          { label:'Countries tracked', value:num((atlas.countries || []).length) },
          { label:'Certified projects', value:num(atlas.certified_projects) },
          { label:'Open alerts', value:num(atlas.open_alerts) },
          { label:'Professionalism avg', value:fmt(atlas.professionalism_index_avg) },
        ]), '')}
        ${panel('Published reports', 'ATLAS™ reports', listTemplate(reports, r => row(r.title || r.report_type, `${fmt(r.country_scope)} • ${fmt(r.period_label)} • by ${fmt(r.generated_by)}`, r.status), 'No reports yet.'), `<div class="actions-row"><button class="btn btn-sm" data-open-create="report">Publish report</button><button class="btn btn-sm btn-ghost" data-open-create="atlas_subscription">New subscription</button></div>`)}
      </div>
      <div>${panel('Institutional subscribers', 'ATLAS™ access', listTemplate(subs, s => row(s.subscriber_name, `${fmt(s.subscriber_type)} • ${fmt(s.country_scope)} • ${fmt(s.access_tier)}`, s.status), 'No subscriptions yet.'), '')}</div>
    </div>`;
  bindDynamicActions();
}

function renderAcademy(){
  const paths = itemsOf(state.datasets.academyPaths);
  const courses = itemsOf(state.datasets.academyCourses);
  const enrollments = itemsOf(state.datasets.academyEnrollments);
  const credentials = itemsOf(state.datasets.academyCredentials);
  const advancement = state.datasets.academyAdvancement || {};
  setHero('Band progression must be earned through demonstrated evidence.', 'ACADEMY™ now covers paths, courses, enrollments, completions, and awarded credentials in one enterprise surface.', [`${safeCount(paths)} paths`, `${safeCount(courses)} courses`, `${safeCount(enrollments)} enrollments`, `${safeCount(credentials)} credentials`]);
  setKpis([
    { label:'Current band', value:fmt(advancement.current_band) },
    { label:'Recommended next', value:fmt(advancement.recommended_next_band) },
    { label:'Completed courses', value:num(advancement.completed_courses) },
    { label:'Completed paths', value:num(advancement.completed_paths) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Learning paths', 'ACADEMY™', listTemplate(paths, p => row(p.code || p.title, `${fmt(p.target_band)} • ${fmt(p.discipline_scope)} • ${fmt(p.description)}`, p.status || 'active'), 'No paths available.'), `<div class="actions-row"><button class="btn btn-sm" data-open-create="path">Create path</button><button class="btn btn-sm btn-ghost" data-open-create="course">Create course</button></div>`)}
        ${panel('Enrollments', 'ACADEMY™ progression', listTemplate(enrollments, e => row(`Enrollment ${e.id} • ${fmt(e.course_code)}`, `Professional ${fmt(e.professional_id)} • Path ${fmt(e.path_code)} • Score ${fmt(e.score)}`, e.status, `<button class="btn btn-sm btn-ghost" data-open-complete-enrollment="${e.id}">Complete</button>`), 'No enrollments yet.'), `<button class="btn btn-sm" data-open-create="enrollment">Enroll in course</button>`)}
      </div>
      <div class="stack">
        ${panel('Course catalogue', 'ACADEMY™', listTemplate(courses, c => row(c.code || c.title, `${fmt(c.path_code)} • ${fmt(c.delivery_mode)} • ${fmt(c.hours)} hours`, c.status || 'active', `<button class="btn btn-sm btn-ghost" data-open-create="enrollment" data-course-code="${c.code}">Enroll</button>`), 'No courses available.'), '')}
        ${panel('Credentials awarded', 'Professional advancement', listTemplate(credentials, c => row(c.credential_title || `Credential ${c.id}`, `Professional ${fmt(c.professional_id)} • ${fmt(c.path_code)}`, c.status || 'awarded'), 'No credentials awarded.'), '')}
      </div>
    </div>`;
  bindDynamicActions();
}

function renderClone(){
  const summary = state.datasets.cloneSummary || {};
  const countries = itemsOf(state.datasets.cloneCountries);
  const tenants = itemsOf(state.datasets.cloneTenants);
  const programs = itemsOf(state.datasets.cloneLaunchPrograms);
  const rules = itemsOf(state.datasets.cloneRevenueRules);
  setHero('Country expansion is a governed operating system, not a slide deck.', 'CLONE™ now includes countries, tenants, launch programs, and revenue-sharing rules in the main frontend.', [`${safeCount(countries)} countries`, `${safeCount(tenants)} tenants`, `${safeCount(programs)} programs`, `${safeCount(rules)} rules`]);
  setKpis([
    { label:'Countries', value:num(summary.total_countries ?? countries.length) },
    { label:'Active tenants', value:num(summary.active_tenants ?? tenants.length) },
    { label:'Average readiness', value:fmt(summary.avg_readiness) },
    { label:'Launches in progress', value:num(summary.launches_in_progress ?? programs.filter(p => p.status === 'active').length) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Country rollout register', 'CLONE™ countries', listTemplate(countries, c => row(`${fmt(c.code)} • ${fmt(c.name)}`, `${fmt(c.region)} • readiness ${fmt(c.readiness_score)} • appetite ${fmt(c.regulator_appetite)}`, c.launch_stage || c.status), 'No countries configured.'), `<div class="actions-row"><button class="btn btn-sm" data-open-create="country">Add country</button><button class="btn btn-sm btn-ghost" data-open-create="tenant">Add tenant</button></div>`)}
        ${panel('Launch programs', 'Expansion execution', listTemplate(programs, p => row(p.title, `${fmt(p.country_code)} • ${fmt(p.phase)} • progress ${fmt(p.progress)}%`, p.status), 'No launch programs yet.'), `<button class="btn btn-sm" data-open-create="launch_program">Create launch program</button>`)}
      </div>
      <div class="stack">
        ${panel('Country tenants', 'Operating rights', listTemplate(tenants, t => row(t.operator_name, `${fmt(t.country_code)} • ${fmt(t.license_type)} • share ${fmt(t.revenue_share_pct)}%`, t.launch_status || t.status), 'No tenants yet.'), '')}
        ${panel('Revenue share rules', 'Unit economics', listTemplate(rules, r => row(`${fmt(r.country_code)} • ${fmt(r.module_code)}`, `local ${fmt(r.local_operator_pct)}% • platform ${fmt(r.central_platform_pct)}% • government ${fmt(r.government_program_pct)}%`, r.status), 'No revenue rules yet.'), `<button class="btn btn-sm" data-open-create="revenue_rule">Create revenue rule</button>`)}
      </div>
    </div>`;
  bindDynamicActions();
}

function renderGovernance(){
  const dashboard = state.datasets.governanceDashboard || {};
  const members = itemsOf(state.datasets.governanceMembers);
  const committees = itemsOf(state.datasets.governanceCommittees);
  const resolutions = itemsOf(state.datasets.governanceResolutions);
  setHero('Legitimacy is part of the moat.', 'Governance now covers CST appointments, committees, resolutions, and voting actions inside the enterprise frontend.', [`${safeCount(members)} CST members`, `${safeCount(committees)} committees`, `${safeCount(resolutions)} resolutions`]);
  setKpis([
    { label:'Active members', value:num(dashboard.active_members ?? members.length) },
    { label:'Active committees', value:num(dashboard.active_committees ?? committees.length) },
    { label:'Open resolutions', value:num(dashboard.open_resolutions) },
    { label:'Passed resolutions', value:num(dashboard.passed_resolutions) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Council composition', 'CST appointments', listTemplate(members, m => row(`Professional ${fmt(m.professional_id)} • ${fmt(m.appointment_title)}`, `${dateFmt(m.term_start)} → ${dateFmt(m.term_end)} • voting ${m.voting_rights ? 'enabled' : 'disabled'}`, m.status), 'No members available.'), `<div class="actions-row"><button class="btn btn-sm" data-open-create="member">Appoint member</button><button class="btn btn-sm btn-ghost" data-open-create="committee">Create committee</button></div>`)}
        ${panel('Committees', 'Delegated governance bodies', listTemplate(committees, c => row(`${fmt(c.code)} • ${fmt(c.name)}`, fmt(c.scope), c.status), 'No committees available.'), '')}
      </div>
      <div>${panel('Resolutions and votes', 'Normative control', listTemplate(resolutions, r => row(r.resolution_uid || r.title, `${fmt(r.title)} • ${fmt(r.committee_code)} • effective ${dateFmt(r.effective_date)}`, r.status, `<div class="actions-row"><button class="btn btn-sm btn-ghost" data-open-create="vote" data-resolution-uid="${r.resolution_uid}">Vote</button></div>`), 'No resolutions available.'), `<div class="actions-row"><button class="btn btn-sm" data-open-create="resolution">Draft resolution</button></div>` )}</div>
    </div>`;
  bindDynamicActions();
}

function renderRegulatory(){
  const readiness = state.datasets.regulatoryReadiness || {};
  const regs = itemsOf(state.datasets.regulations);
  const consultations = itemsOf(state.datasets.consultations);
  const mappings = itemsOf(state.datasets.complianceMappings);
  setHero('Regulatory co-creation must be operational, not rhetorical.', 'The frontend now manages regulations, consultations, and module-to-standard mappings as first-class institutional workflows.', [`${safeCount(regs)} regulations`, `${safeCount(consultations)} consultations`, `${safeCount(mappings)} mappings`]);
  setKpis([
    { label:'Tracked countries', value:num(readiness.tracked_countries) },
    { label:'Draft regulations', value:num(readiness.draft_regulations) },
    { label:'Open consultations', value:num(readiness.open_consultations) },
    { label:'Mapped requirements', value:num(readiness.mapped_requirements) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Regulations', 'Regulatory framework', listTemplate(regs, r => row(r.regulation_code || r.title, `${fmt(r.country_code)} • ${fmt(r.category)} • ${fmt(r.summary)}`, r.status), 'No regulations available.'), `<div class="actions-row"><button class="btn btn-sm" data-open-create="regulation">Create regulation</button><button class="btn btn-sm btn-ghost" data-open-create="consultation">Open consultation</button></div>`)}
        ${panel('Consultations', 'Regulatory engagement', listTemplate(consultations, c => row(c.consultation_uid || c.title, `${fmt(c.country_code)} • ${fmt(c.consultation_type)} • open ${fmt(c.opened_at_label)}`, c.status), 'No consultations available.'), '')}
      </div>
      <div>${panel('Compliance mappings', 'Module-to-standard map', listTemplate(mappings, m => row(`${fmt(m.country_code)} • ${fmt(m.module_code)}`, `${fmt(m.standard_code)} • ${fmt(m.requirement_summary)}`, m.status), 'No mappings available.'), `<button class="btn btn-sm" data-open-create="mapping">Add mapping</button>` )}</div>
    </div>`;
  bindDynamicActions();
}

function renderPay(){
  const milestones = itemsOf(state.datasets.milestones);
  const payments = itemsOf(state.datasets.payments);
  setHero('Money follows structural truth.', 'PAY™ now supports gate evaluation and release actions directly from the frontend, alongside the milestone and escrow ledgers.', [`${safeCount(milestones)} milestones`, `${safeCount(payments)} payments`, `${money(sum(payments.map(p => p.amount || 0)), 'USD')} released`]);
  setKpis([
    { label:'Milestones', value:num(milestones.length) },
    { label:'Released', value:num(milestones.filter(m => m.status === 'released').length) },
    { label:'Payments', value:num(payments.length) },
    { label:'Escrow released', value:money(sum(payments.map(p => p.amount || 0)), 'USD') }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Milestone gate register', 'PAY™', table(
        ['Project','Phase','Required SHI','Amount','Status','Action'],
        milestones.map(m => `<tr><td>${fmt(m.project_uid)}</td><td>${fmt(m.name)}</td><td>${fmt(m.required_shi)}</td><td>${money(m.amount, m.currency)}</td><td>${badge(m.status)}</td><td><div class="actions-row"><button class="btn btn-sm btn-ghost" data-evaluate-milestone="${m.id}">Evaluate</button><button class="btn btn-sm" data-release-milestone="${m.id}">Release</button></div></td></tr>`)
      ), '')}</div>
      <div>${panel('Released payment trail', 'Escrow output', listTemplate(payments.slice(0,12), p => row(p.tx_id || `Payment ${p.id}`, `${money(p.amount, p.currency)} • ${fmt(p.project_uid)} • ${dateFmt(p.date)}`, p.status), 'No payments found.'), '')}</div>
    </div>`;
  bindDynamicActions();
}

function renderSeal(){
  const certs = itemsOf(state.datasets.certifications);
  const projects = itemsOf(state.datasets.projects);
  setHero('Physical certification with public verifiability.', 'SEAL™ now supports eligibility checks, issuance, and public certificate verification from the same canonical frontend.', [`${safeCount(certs)} certifications`, `${num(projects.length)} projects in pipeline`]);
  setKpis([
    { label:'Certifications', value:num(certs.length) },
    { label:'Average certified SHI', value:avg(certs.map(c => c.shi_composite)) },
    { label:'Pending ceremony', value:num(certs.filter(c => c.status === 'pending_ceremony').length) },
    { label:'Issued/ready', value:num(certs.filter(c => ['issued','pending_ceremony'].includes(c.status)).length) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Certification ledger', 'SEAL™', listTemplate(certs, c => row(c.project_uid, `${fmt(c.type)} • Plate ${fmt(c.physical_plate)} • SHI ${fmt(c.shi_composite)}`, c.status, `<button class="btn btn-sm btn-ghost" data-verify-seal="${c.project_uid}">Verify public record</button>`), 'No certifications available.'), `<button class="btn btn-sm" data-open-create="issue_seal">Issue certification</button>`)}</div>
      <div>${panel('Eligibility probe', 'Project certification gate', listTemplate(projects.slice(0,8), p => row(p.uid, `${fmt(p.name)} • SHI ${fmt(p.shi)} • ${fmt(p.phase)}`, p.status, `<button class="btn btn-sm btn-ghost" data-check-eligibility="${p.uid}">Check eligibility</button>`), 'No projects available.'), '')}</div>
    </div>`;
  bindDynamicActions();
}

function renderMonitor(){
  const sensors = itemsOf(state.datasets.sensors);
  const alerts = itemsOf(state.datasets.alerts);
  setHero('Operational sensing closes the gap between execution truth and in-service behavior.', 'MONITOR™ now includes live sensor records, alerts, and direct reading capture from the frontend.', [`${safeCount(sensors)} sensors`, `${safeCount(alerts)} alerts`]);
  setKpis([
    { label:'Sensors', value:num(sensors.length) },
    { label:'Open alerts', value:num(alerts.filter(a => String(a.status).toLowerCase() !== 'resolved').length) },
    { label:'Normal sensors', value:num(sensors.filter(s => s.status === 'normal').length) },
    { label:'Threshold risks', value:num(alerts.filter(a => String(a.severity || a.status).toLowerCase().includes('critical')).length) }
  ]);
  el.workspace.innerHTML = `
    <div class="module-grid">
      <div>${panel('Sensor registry', 'MONITOR™', listTemplate(sensors, s => row(`Sensor ${fmt(s.id)} • ${fmt(s.type)}`, `${fmt(s.component_uid)} • ${fmt(s.current_reading)} ${fmt(s.unit)} • threshold ${fmt(s.threshold)}`, s.status), 'No sensors available.'), `<button class="btn btn-sm" data-open-create="sensor_reading">Capture reading</button>` )}</div>
      <div>${panel('Alert stream', 'Threshold intelligence', listTemplate(alerts, a => row(`Alert ${fmt(a.id)} • ${fmt(a.alert_type || a.sensor_type)}`, `${fmt(a.component_uid)} • ${fmt(a.message || a.detail || a.status)}`, a.status || a.severity), 'No alerts available.'), '')}</div>
    </div>`;
  bindDynamicActions();
}

function renderLex(){
  const disputes = itemsOf(state.datasets.disputes);
  setHero('Disputes should resolve from evidence, not from theatre.', 'LEX™ now supports dispute intake and determination actions from the frontend.', [`${safeCount(disputes)} disputes`, `${num(disputes.filter(d => d.status === 'open').length)} open`]);
  setKpis([
    { label:'Disputes', value:num(disputes.length) },
    { label:'Open', value:num(disputes.filter(d => d.status === 'open').length) },
    { label:'Resolved', value:num(disputes.filter(d => d.status === 'resolved').length) },
    { label:'Components referenced', value:num(new Set(disputes.map(d => d.component_uid).filter(Boolean)).size) }
  ]);
  el.workspace.innerHTML = panel('Dispute register', 'LEX™', listTemplate(disputes, d => row(d.uid || `Dispute ${d.id}`, `${fmt(d.project_uid)} • ${fmt(d.type)} • against ${fmt(d.against_party)}`, d.status, d.status === 'open' ? `<button class="btn btn-sm btn-ghost" data-resolve-dispute="${d.id}">Resolve</button>` : ''), 'No disputes available.'), `<button class="btn btn-sm" data-open-create="dispute">Open dispute</button>`);
  bindDynamicActions();
}

function bindDynamicActions(){
  document.querySelectorAll('[data-open-create]').forEach(button => button.addEventListener('click', () => openCreateModal(button.dataset.openCreate, button.dataset)));
  document.querySelectorAll('[data-project-detail]').forEach(button => button.addEventListener('click', () => openProjectDetail(button.dataset.projectDetail)));
  document.querySelectorAll('[data-component-detail]').forEach(button => button.addEventListener('click', () => openComponentDetail(button.dataset.componentDetail)));
  document.querySelectorAll('[data-mark-read]').forEach(button => button.addEventListener('click', () => markNotificationRead(button.dataset.markRead)));
  document.querySelectorAll('[data-verify-seal]').forEach(button => button.addEventListener('click', () => verifySeal(button.dataset.verifySeal)));
  document.querySelectorAll('[data-evaluate-app]').forEach(button => button.addEventListener('click', () => evaluateApplication(button.dataset.evaluateApp)));
  document.querySelectorAll('[data-evaluate-milestone]').forEach(button => button.addEventListener('click', () => evaluateMilestone(button.dataset.evaluateMilestone)));
  document.querySelectorAll('[data-release-milestone]').forEach(button => button.addEventListener('click', () => releaseMilestone(button.dataset.releaseMilestone)));
  document.querySelectorAll('[data-check-eligibility]').forEach(button => button.addEventListener('click', () => checkEligibility(button.dataset.checkEligibility)));
  document.querySelectorAll('[data-resolve-dispute]').forEach(button => button.addEventListener('click', () => openResolveDisputeModal(button.dataset.resolveDispute)));
  document.querySelectorAll('[data-open-complete-enrollment]').forEach(button => button.addEventListener('click', () => openCompleteEnrollmentModal(button.dataset.openCompleteEnrollment)));
}

async function evaluateMilestone(id){
  try { const data = await request(`/pay/milestones/${id}/evaluate`, { method:'POST' }); openModal('Milestone gate evaluation', 'PAY™ decision', `<pre class="note code">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`);} catch(error){toast(error.message,'error');}
}
async function releaseMilestone(id){
  try { const data = await request(`/pay/milestones/${id}/release`, { method:'POST' }); openModal('Payment released', 'PAY™', `<pre class="note code">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`); await loadAllData(); } catch(error){toast(error.message,'error');}
}
async function checkEligibility(projectUid){
  try { const data = await request(`/seal/projects/${encodeURIComponent(projectUid)}/eligibility`); openModal('Certification eligibility', 'SEAL™ gate', `<pre class="note code">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`);} catch(error){toast(error.message,'error');}
}
function openResolveDisputeModal(id){
  openModal('Resolve dispute', 'LEX™ determination', `<form id="resolveDisputeForm" class="form-grid one"><label><span>Resolution</span><textarea name="resolution" rows="6" required></textarea></label><button class="btn btn-primary" type="submit">Issue determination</button></form>`);
  const form=document.getElementById('resolveDisputeForm');
  form.addEventListener('submit', async (event)=>{event.preventDefault(); try { await request(`/lex/disputes/${id}/resolve`, { method:'POST', body: JSON.stringify({ resolution: new FormData(form).get('resolution') }) }); closeModal(); toast('Dispute resolved.','success'); await loadAllData(); } catch(error){ toast(error.message,'error'); }});
}
function openCompleteEnrollmentModal(id){
  openModal('Complete enrollment', 'ACADEMY™', `<form id="completeEnrollmentForm" class="form-grid one"><label><span>Score</span><input name="score" type="number" min="0" max="100" value="85" required /></label><button class="btn btn-primary" type="submit">Complete enrollment</button></form>`);
  const form=document.getElementById('completeEnrollmentForm');
  form.addEventListener('submit', async (event)=>{event.preventDefault(); try { await request(`/academy/enrollments/${id}/complete`, { method:'POST', body: JSON.stringify({ score: Number(new FormData(form).get('score')) }) }); closeModal(); toast('Enrollment completed.','success'); await loadAllData(); } catch(error){ toast(error.message,'error'); }});
}

function openCreateModal(kind, seed={}){
  const forms = {
    project: projectForm,
    component: componentForm,
    evidence: evidenceForm,
    inspection: inspectionForm,
    tender: tenderForm,
    report: reportForm,
    product: productForm,
    application: applicationForm,
    path: pathForm,
    course: courseForm,
    atlas_subscription: atlasSubscriptionForm,
    member: memberForm,
    committee: committeeForm,
    resolution: resolutionForm,
    vote: ()=>voteForm(seed.resolutionUid || ''),
    country: countryForm,
    tenant: tenantForm,
    launch_program: launchProgramForm,
    revenue_rule: revenueRuleForm,
    regulation: regulationForm,
    consultation: consultationForm,
    mapping: mappingForm,
    dispute: disputeForm,
    material: materialForm,
    sensor_reading: sensorReadingForm,
    enrollment: ()=>enrollmentForm(seed.courseCode || ''),
    issue_seal: issueSealForm,
    feature_flag: featureFlagForm,
    country_config: countryConfigForm,
    policy_rule: policyRuleForm,
    policy_eval: policyEvalForm,
    workflow_definition: workflowDefinitionForm,
    workflow_state: workflowStateForm,
    workflow_transition: workflowTransitionForm,
    workflow_instance: workflowInstanceForm,
    workflow_action: workflowActionForm,
  };
  const renderer = forms[kind];
  if (!renderer) return toast('Form not configured.', 'error');
  const config = renderer();
  openModal(config.title, config.eyebrow, config.body);
  const form = document.getElementById(config.formId);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const result = await config.submit(new FormData(form));
      closeModal();
      if (result && config.showResult) openModal(config.title, config.eyebrow, `<pre class="note code">${escapeHtml(JSON.stringify(result, null, 2))}</pre>`);
      await loadAllData();
    } catch (error) {
      toast(error.message, 'error');
    }
  });
}

function optionsFor(items, valueKey, labelFn){ return items.map(i => `<option value="${escapeHtml(i[valueKey])}">${escapeHtml(labelFn(i))}</option>`).join(''); }
function projectsOptions(){ return optionsFor(itemsOf(state.datasets.projects), 'uid', i => `${i.uid} — ${i.name}`); }
function componentsOptions(){ return optionsFor(itemsOf(state.datasets.components), 'uid', i => `${i.uid} — ${i.type || 'Component'}`); }
function coursesOptions(){ return optionsFor(itemsOf(state.datasets.academyCourses), 'code', i => `${i.code} — ${i.title}`); }
function professionalsOptions(){ return optionsFor(itemsOf(state.datasets.professionals), 'id', i => `${i.id} — ${i.name}`); }
function countriesOptions(){ return optionsFor(itemsOf(state.datasets.cloneCountries), 'code', i => `${i.code} — ${i.name}`); }
function committeesOptions(){ return optionsFor(itemsOf(state.datasets.governanceCommittees), 'code', i => `${i.code} — ${i.name}`); }
function productsOptions(){ return optionsFor(itemsOf(state.datasets.verifundProducts), 'code', i => `${i.code} — ${i.name}`); }
function milestonesOptions(){ return optionsFor(itemsOf(state.datasets.milestones), 'id', i => `${i.id} — ${i.project_uid} — ${i.name}`); }
function workflowsGuessOptions(){ return ['pay_gate','seal_issue','evidence_approval','regulatory_issuance'].map(v=>`<option value="${v}">${v}</option>`).join(''); }

function atlasSubscriptionForm(){ return { title:'Create ATLAS subscription', eyebrow:'ATLAS™', formId:'atlasSubscriptionForm', body:`<form id="atlasSubscriptionForm" class="form-grid two"><label><span>Subscriber name</span><input name="subscriber_name" required></label><label><span>Subscriber type</span><input name="subscriber_type" value="government"></label><label><span>Country scope</span><input name="country_scope"></label><label><span>Access tier</span><input name="access_tier" value="standard"></label><label><span>Status</span><input name="status" value="active"></label><button class="btn btn-primary" type="submit">Create subscription</button></form>`, submit: fd=>request('/atlas/subscriptions',{method:'POST',body:JSON.stringify({subscriber_name:fd.get('subscriber_name'),subscriber_type:fd.get('subscriber_type'),country_scope:fd.get('country_scope')||null,access_tier:fd.get('access_tier'),status:fd.get('status')})})}; }
function memberForm(){ return { title:'Appoint CST member', eyebrow:'Governance', formId:'memberForm', body:`<form id="memberForm" class="form-grid two"><label><span>Professional</span><select name="professional_id" required>${professionalsOptions()}</select></label><label><span>Appointment title</span><input name="appointment_title" value="Council Member"></label><label><span>Voting rights</span><select name="voting_rights"><option value="true">true</option><option value="false">false</option></select></label><label><span>Term start</span><input name="term_start" type="date"></label><label><span>Term end</span><input name="term_end" type="date"></label><label><span>Status</span><input name="status" value="active"></label><button class="btn btn-primary" type="submit">Appoint member</button></form>`, submit: fd=>request('/governance/members',{method:'POST',body:JSON.stringify({professional_id:Number(fd.get('professional_id')),appointment_title:fd.get('appointment_title'),voting_rights:fd.get('voting_rights')==='true',term_start:fd.get('term_start')||null,term_end:fd.get('term_end')||null,status:fd.get('status')})})}; }
function committeeForm(){ return { title:'Create committee', eyebrow:'Governance', formId:'committeeForm', body:`<form id="committeeForm" class="form-grid one"><label><span>Code</span><input name="code" required></label><label><span>Name</span><input name="name" required></label><label><span>Scope</span><textarea name="scope" rows="4"></textarea></label><label><span>Status</span><input name="status" value="active"></label><button class="btn btn-primary" type="submit">Create committee</button></form>`, submit: fd=>request('/governance/committees',{method:'POST',body:JSON.stringify({code:fd.get('code'),name:fd.get('name'),scope:fd.get('scope')||null,status:fd.get('status')})})}; }
function resolutionForm(){ return { title:'Draft resolution', eyebrow:'Governance', formId:'resolutionForm', body:`<form id="resolutionForm" class="form-grid two"><label><span>Resolution UID</span><input name="resolution_uid" required></label><label><span>Committee</span><select name="committee_code" required>${committeesOptions()}</select></label><label><span>Title</span><input name="title" required></label><label><span>Resolution type</span><input name="resolution_type" value="standard"></label><label style="grid-column:1/-1"><span>Body text</span><textarea name="body_text" rows="6" required></textarea></label><label><span>Status</span><input name="status" value="draft"></label><label><span>Effective date</span><input name="effective_date" type="date"></label><button class="btn btn-primary" type="submit">Create resolution</button></form>`, submit: fd=>request('/governance/resolutions',{method:'POST',body:JSON.stringify({resolution_uid:fd.get('resolution_uid'),committee_code:fd.get('committee_code'),title:fd.get('title'),resolution_type:fd.get('resolution_type'),body_text:fd.get('body_text'),status:fd.get('status'),effective_date:fd.get('effective_date')||null})})}; }
function voteForm(resolutionUid){ return { title:'Cast governance vote', eyebrow:'Governance', formId:'voteForm', body:`<form id="voteForm" class="form-grid one"><label><span>Resolution UID</span><input name="resolution_uid" value="${escapeHtml(resolutionUid)}" required></label><label><span>Vote</span><select name="vote"><option value="yes">yes</option><option value="no">no</option><option value="abstain">abstain</option></select></label><label><span>Rationale</span><textarea name="rationale" rows="5"></textarea></label><button class="btn btn-primary" type="submit">Submit vote</button></form>`, submit: fd=>request('/governance/votes',{method:'POST',body:JSON.stringify({resolution_uid:fd.get('resolution_uid'),vote:fd.get('vote'),rationale:fd.get('rationale')||null})})}; }
function countryForm(){ return { title:'Add country rollout', eyebrow:'CLONE™', formId:'countryForm', body:`<form id="countryForm" class="form-grid two"><label><span>Code</span><input name="code" required></label><label><span>Name</span><input name="name" required></label><label><span>Region</span><input name="region"></label><label><span>Launch stage</span><input name="launch_stage" value="pipeline"></label><label><span>Readiness score</span><input name="readiness_score" type="number" value="0" min="0" max="100"></label><label><span>Regulator appetite</span><input name="regulator_appetite"></label><label><span>Status</span><input name="status" value="active"></label><button class="btn btn-primary" type="submit">Add country</button></form>`, submit: fd=>request('/clone/countries',{method:'POST',body:JSON.stringify({code:fd.get('code'),name:fd.get('name'),region:fd.get('region')||null,launch_stage:fd.get('launch_stage'),readiness_score:Number(fd.get('readiness_score')||0),regulator_appetite:fd.get('regulator_appetite')||null,status:fd.get('status')})})}; }
function tenantForm(){ return { title:'Create country tenant', eyebrow:'CLONE™', formId:'tenantForm', body:`<form id="tenantForm" class="form-grid two"><label><span>Country</span><select name="country_code" required>${countriesOptions()}</select></label><label><span>Operator name</span><input name="operator_name" required></label><label><span>License type</span><input name="license_type" value="country_franchise"></label><label><span>Revenue share %</span><input name="revenue_share_pct" type="number" value="0"></label><label><span>Launch status</span><input name="launch_status" value="pending"></label><label><span>Start date</span><input name="start_date" type="date"></label><label><span>End date</span><input name="end_date" type="date"></label><button class="btn btn-primary" type="submit">Create tenant</button></form>`, submit: fd=>request('/clone/tenants',{method:'POST',body:JSON.stringify({country_code:fd.get('country_code'),operator_name:fd.get('operator_name'),license_type:fd.get('license_type'),revenue_share_pct:Number(fd.get('revenue_share_pct')||0),launch_status:fd.get('launch_status'),start_date:fd.get('start_date')||null,end_date:fd.get('end_date')||null})})}; }
function launchProgramForm(){ return { title:'Create launch program', eyebrow:'CLONE™', formId:'launchProgramForm', body:`<form id="launchProgramForm" class="form-grid two"><label><span>Country</span><select name="country_code" required>${countriesOptions()}</select></label><label><span>Title</span><input name="title" required></label><label><span>Phase</span><input name="phase" value="readiness"></label><label><span>Progress</span><input name="progress" type="number" value="0" min="0" max="100"></label><label><span>Owner professional</span><select name="owner_professional_id">${professionalsOptions()}</select></label><label><span>Status</span><input name="status" value="active"></label><label style="grid-column:1/-1"><span>Notes</span><textarea name="notes" rows="4"></textarea></label><button class="btn btn-primary" type="submit">Create program</button></form>`, submit: fd=>request('/clone/launch-programs',{method:'POST',body:JSON.stringify({country_code:fd.get('country_code'),title:fd.get('title'),phase:fd.get('phase'),progress:Number(fd.get('progress')||0),owner_professional_id:fd.get('owner_professional_id')?Number(fd.get('owner_professional_id')):null,status:fd.get('status'),notes:fd.get('notes')||null})})}; }
function revenueRuleForm(){ return { title:'Create revenue rule', eyebrow:'CLONE™', formId:'revenueRuleForm', body:`<form id="revenueRuleForm" class="form-grid two"><label><span>Country</span><select name="country_code" required>${countriesOptions()}</select></label><label><span>Module code</span><input name="module_code" value="PAY"></label><label><span>Local operator %</span><input name="local_operator_pct" type="number" value="0"></label><label><span>Central platform %</span><input name="central_platform_pct" type="number" value="0"></label><label><span>Government program %</span><input name="government_program_pct" type="number" value="0"></label><label><span>Status</span><input name="status" value="active"></label><button class="btn btn-primary" type="submit">Create rule</button></form>`, submit: fd=>request('/clone/revenue-share-rules',{method:'POST',body:JSON.stringify({country_code:fd.get('country_code'),module_code:fd.get('module_code'),local_operator_pct:Number(fd.get('local_operator_pct')||0),central_platform_pct:Number(fd.get('central_platform_pct')||0),government_program_pct:Number(fd.get('government_program_pct')||0),status:fd.get('status')})})}; }
function regulationForm(){ return { title:'Create regulation', eyebrow:'Regulatory', formId:'regulationForm', body:`<form id="regulationForm" class="form-grid one"><label><span>Country</span><select name="country_code" required>${countriesOptions()}</select></label><label><span>Regulation code</span><input name="regulation_code" required></label><label><span>Title</span><input name="title" required></label><label><span>Category</span><input name="category" value="construction_integrity"></label><label><span>Status</span><input name="status" value="draft"></label><label><span>Summary</span><textarea name="summary" rows="5"></textarea></label><button class="btn btn-primary" type="submit">Create regulation</button></form>`, submit: fd=>request('/regulatory/regulations',{method:'POST',body:JSON.stringify({country_code:fd.get('country_code'),regulation_code:fd.get('regulation_code'),title:fd.get('title'),category:fd.get('category'),status:fd.get('status'),summary:fd.get('summary')||null})})}; }
function consultationForm(){ return { title:'Open consultation', eyebrow:'Regulatory', formId:'consultationForm', body:`<form id="consultationForm" class="form-grid two"><label><span>Consultation UID</span><input name="consultation_uid" required></label><label><span>Country</span><select name="country_code" required>${countriesOptions()}</select></label><label><span>Title</span><input name="title" required></label><label><span>Type</span><input name="consultation_type" value="regulatory"></label><label><span>Status</span><input name="status" value="open"></label><label><span>Opened label</span><input name="opened_at_label" value="Q2 2026"></label><label><span>Closed label</span><input name="closed_at_label"></label><button class="btn btn-primary" type="submit">Open consultation</button></form>`, submit: fd=>request('/regulatory/consultations',{method:'POST',body:JSON.stringify({consultation_uid:fd.get('consultation_uid'),country_code:fd.get('country_code'),title:fd.get('title'),consultation_type:fd.get('consultation_type'),status:fd.get('status'),opened_at_label:fd.get('opened_at_label')||null,closed_at_label:fd.get('closed_at_label')||null})})}; }
function mappingForm(){ return { title:'Add compliance mapping', eyebrow:'Regulatory', formId:'mappingForm', body:`<form id="mappingForm" class="form-grid one"><label><span>Country</span><select name="country_code" required>${countriesOptions()}</select></label><label><span>Standard code</span><input name="standard_code" required></label><label><span>Module code</span><input name="module_code" required></label><label><span>Requirement summary</span><textarea name="requirement_summary" rows="5" required></textarea></label><label><span>Status</span><input name="status" value="mapped"></label><button class="btn btn-primary" type="submit">Create mapping</button></form>`, submit: fd=>request('/regulatory/compliance-mappings',{method:'POST',body:JSON.stringify({country_code:fd.get('country_code'),standard_code:fd.get('standard_code'),module_code:fd.get('module_code'),requirement_summary:fd.get('requirement_summary'),status:fd.get('status')})})}; }
function disputeForm(){ return { title:'Open dispute', eyebrow:'LEX™', formId:'disputeForm', body:`<form id="disputeForm" class="form-grid two"><label><span>UID</span><input name="uid" required></label><label><span>Project</span><select name="project_uid" required>${projectsOptions()}</select></label><label><span>Component</span><select name="component_uid">${componentsOptions()}</select></label><label><span>Type</span><input name="type" value="Technical Execution"></label><label><span>Against party</span><input name="against_party" required></label><label style="grid-column:1/-1"><span>Description</span><textarea name="description" rows="5" required></textarea></label><button class="btn btn-primary" type="submit">Open dispute</button></form>`, submit: fd=>request('/lex/disputes',{method:'POST',body:JSON.stringify({uid:fd.get('uid'),project_uid:fd.get('project_uid'),component_uid:fd.get('component_uid')||null,type:fd.get('type'),against_party:fd.get('against_party'),description:fd.get('description')})})}; }
function materialForm(){ return { title:'Register material batch', eyebrow:'ORIGIN™', formId:'materialForm', body:`<form id="materialForm" class="form-grid two"><label><span>Batch UID</span><input name="batch_uid" required></label><label><span>Name</span><input name="name" required></label><label><span>Grade</span><input name="grade" required></label><label><span>Supplier</span><input name="supplier" required></label><label><span>Country</span><input name="country"></label><label><span>Certificate number</span><input name="cert_number"></label><label><span>Verified</span><select name="verified"><option value="true">true</option><option value="false">false</option></select></label><label><span>Required strength</span><input name="required_strength" type="number" value="0"></label><label><span>Test strength</span><input name="test_strength" type="number" value="0"></label><label><span>Status</span><input name="status" value="approved"></label><button class="btn btn-primary" type="submit">Register material</button></form>`, submit: fd=>request('/materials',{method:'POST',body:JSON.stringify({batch_uid:fd.get('batch_uid'),name:fd.get('name'),grade:fd.get('grade'),supplier:fd.get('supplier'),country:fd.get('country')||null,cert_number:fd.get('cert_number')||null,verified:fd.get('verified')==='true',required_strength:Number(fd.get('required_strength')||0),test_strength:Number(fd.get('test_strength')||0),status:fd.get('status')})})}; }
function sensorReadingForm(){ return { title:'Capture sensor reading', eyebrow:'MONITOR™', formId:'sensorReadingForm', body:`<form id="sensorReadingForm" class="form-grid one"><label><span>Sensor</span><select name="sensor_id" required>${optionsFor(itemsOf(state.datasets.sensors),'id',i=>`${i.id} — ${i.type} — ${i.component_uid}`)}</select></label><label><span>Reading</span><input name="reading" type="number" step="0.01" required></label><button class="btn btn-primary" type="submit">Capture reading</button></form>`, submit: async fd=>{ const data=await request('/monitor/readings',{method:'POST',body:JSON.stringify({sensor_id:Number(fd.get('sensor_id')),reading:Number(fd.get('reading'))})}); openModal('Sensor reading accepted','MONITOR™',`<pre class="note code">${escapeHtml(JSON.stringify(data,null,2))}</pre>`); return data; }, showResult:false }; }
function enrollmentForm(courseCode=''){ return { title:'Enroll in course', eyebrow:'ACADEMY™', formId:'enrollmentForm', body:`<form id="enrollmentForm" class="form-grid one"><label><span>Course</span><select name="course_code" required>${coursesOptions()}</select></label><button class="btn btn-primary" type="submit">Create enrollment</button></form>`, submit: fd=>request('/academy/enrollments',{method:'POST',body:JSON.stringify({course_code:fd.get('course_code')||courseCode})})}; }
function issueSealForm(){ return { title:'Issue certification', eyebrow:'SEAL™', formId:'issueSealForm', body:`<form id="issueSealForm" class="form-grid one"><label><span>Project</span><select name="project_uid" required>${projectsOptions()}</select></label><label><span>Certificate type</span><input name="certificate_type" value="SEAL-HONOR"></label><label><span>Notes</span><textarea name="notes" rows="5"></textarea></label><button class="btn btn-primary" type="submit">Issue certificate</button></form>`, submit: fd=>request('/seal/issue',{method:'POST',body:JSON.stringify({project_uid:fd.get('project_uid'),certificate_type:fd.get('certificate_type'),notes:fd.get('notes')||null})})}; }
function featureFlagForm(){ return { title:'Set feature flag', eyebrow:'Platform configuration', formId:'featureFlagForm', body:`<form id="featureFlagForm" class="form-grid two"><label><span>Code</span><input name="code" required></label><label><span>Name</span><input name="name" required></label><label><span>Enabled</span><select name="enabled"><option value="true">true</option><option value="false">false</option></select></label><label><span>Environment</span><input name="environment" value="prod"></label><label><span>Tenant code</span><input name="tenant_code"></label><label><span>Country code</span><input name="country_code"></label><label><span>Stability</span><input name="stability" value="stable"></label><button class="btn btn-primary" type="submit">Save flag</button></form>`, submit: async fd=>{ const data=await request('/platformcfg/flags',{method:'POST',body:JSON.stringify({code:fd.get('code'),name:fd.get('name'),enabled:fd.get('enabled')==='true',environment:fd.get('environment')||null,tenant_code:fd.get('tenant_code')||null,country_code:fd.get('country_code')||null,stability:fd.get('stability')})}); return data; }, showResult:true }; }
function countryConfigForm(){ return { title:'Set country configuration', eyebrow:'Platform configuration', formId:'countryConfigForm', body:`<form id="countryConfigForm" class="form-grid one"><label><span>Country code</span><input name="country_code" required></label><label><span>Default workflow variant</span><input name="default_workflow_variant"></label><label><span>Certification rule</span><input name="certification_rule"></label><label><span>Payment rule</span><input name="payment_rule"></label><label><span>Evidence rule</span><input name="evidence_rule"></label><label><span>Regulator override</span><select name="regulator_override"><option value="false">false</option><option value="true">true</option></select></label><label><span>Config JSON</span><textarea name="config_json" rows="6">{}</textarea></label><button class="btn btn-primary" type="submit">Save config</button></form>`, submit: async fd=>request('/platformcfg/country-config',{method:'POST',body:JSON.stringify({country_code:fd.get('country_code'),default_workflow_variant:fd.get('default_workflow_variant')||null,certification_rule:fd.get('certification_rule')||null,payment_rule:fd.get('payment_rule')||null,evidence_rule:fd.get('evidence_rule')||null,regulator_override:fd.get('regulator_override')==='true',config_json:fd.get('config_json')||null})}), showResult:true }; }
function policyRuleForm(){ return { title:'Create policy rule', eyebrow:'Policy engine', formId:'policyRuleForm', body:`<form id="policyRuleForm" class="form-grid two"><label><span>Code</span><input name="code" required></label><label><span>Action</span><input name="action" required></label><label><span>Resource</span><input name="resource" required></label><label><span>Effect</span><input name="effect" value="allow"></label><label><span>Subject role</span><input name="subject_role"></label><label><span>Country code</span><input name="country_code"></label><label><span>Tenant code</span><input name="tenant_code"></label><label style="grid-column:1/-1"><span>Condition expression</span><textarea name="condition_expr" rows="4"></textarea></label><label><span>Is active</span><select name="is_active"><option value="true">true</option><option value="false">false</option></select></label><button class="btn btn-primary" type="submit">Create rule</button></form>`, submit: async fd=>request('/policy/rules',{method:'POST',body:JSON.stringify({code:fd.get('code'),action:fd.get('action'),resource:fd.get('resource'),effect:fd.get('effect'),subject_role:fd.get('subject_role')||null,country_code:fd.get('country_code')||null,tenant_code:fd.get('tenant_code')||null,condition_expr:fd.get('condition_expr')||null,is_active:fd.get('is_active')==='true'})}), showResult:true }; }
function policyEvalForm(){ return { title:'Evaluate policy access', eyebrow:'Policy engine', formId:'policyEvalForm', body:`<form id="policyEvalForm" class="form-grid two"><label><span>Subject</span><input name="subject" required></label><label><span>Subject role</span><input name="subject_role"></label><label><span>Action</span><input name="action" required></label><label><span>Resource</span><input name="resource" required></label><label><span>Country code</span><input name="country_code"></label><label><span>Tenant code</span><input name="tenant_code"></label><button class="btn btn-primary" type="submit">Evaluate</button></form>`, submit: async fd=>request('/policy/evaluate',{method:'POST',body:JSON.stringify({subject:fd.get('subject'),subject_role:fd.get('subject_role')||null,action:fd.get('action'),resource:fd.get('resource'),country_code:fd.get('country_code')||null,tenant_code:fd.get('tenant_code')||null})}), showResult:true }; }
function workflowDefinitionForm(){ return { title:'Create workflow definition', eyebrow:'Workflow engine', formId:'workflowDefinitionForm', body:`<form id="workflowDefinitionForm" class="form-grid two"><label><span>Code</span><input name="code" required></label><label><span>Name</span><input name="name" required></label><label><span>Country code</span><input name="country_code"></label><label><span>Tenant code</span><input name="tenant_code"></label><label><span>Active</span><select name="is_active"><option value="true">true</option><option value="false">false</option></select></label><button class="btn btn-primary" type="submit">Create workflow</button></form>`, submit: async fd=>request('/workflow/definitions',{method:'POST',body:JSON.stringify({code:fd.get('code'),name:fd.get('name'),country_code:fd.get('country_code')||null,tenant_code:fd.get('tenant_code')||null,is_active:fd.get('is_active')==='true'})}), showResult:true }; }
function workflowStateForm(){ return { title:'Create workflow state', eyebrow:'Workflow engine', formId:'workflowStateForm', body:`<form id="workflowStateForm" class="form-grid two"><label><span>Workflow ID</span><input name="workflow_id" type="number" required></label><label><span>Code</span><input name="code" required></label><label><span>Name</span><input name="name" required></label><label><span>Initial</span><select name="is_initial"><option value="false">false</option><option value="true">true</option></select></label><label><span>Terminal</span><select name="is_terminal"><option value="false">false</option><option value="true">true</option></select></label><button class="btn btn-primary" type="submit">Create state</button></form>`, submit: async fd=>request('/workflow/states',{method:'POST',body:JSON.stringify({workflow_id:Number(fd.get('workflow_id')),code:fd.get('code'),name:fd.get('name'),is_initial:fd.get('is_initial')==='true',is_terminal:fd.get('is_terminal')==='true'})}), showResult:true }; }
function workflowTransitionForm(){ return { title:'Create workflow transition', eyebrow:'Workflow engine', formId:'workflowTransitionForm', body:`<form id="workflowTransitionForm" class="form-grid two"><label><span>Workflow ID</span><input name="workflow_id" type="number" required></label><label><span>From state</span><input name="from_state_code" required></label><label><span>To state</span><input name="to_state_code" required></label><label><span>Action code</span><input name="action_code" required></label><label><span>Required role</span><input name="required_role"></label><label><span>Condition expression</span><input name="condition_expr"></label><button class="btn btn-primary" type="submit">Create transition</button></form>`, submit: async fd=>request('/workflow/transitions',{method:'POST',body:JSON.stringify({workflow_id:Number(fd.get('workflow_id')),from_state_code:fd.get('from_state_code'),to_state_code:fd.get('to_state_code'),action_code:fd.get('action_code'),required_role:fd.get('required_role')||null,condition_expr:fd.get('condition_expr')||null})}), showResult:true }; }
function workflowInstanceForm(){ return { title:'Create workflow instance', eyebrow:'Workflow engine', formId:'workflowInstanceForm', body:`<form id="workflowInstanceForm" class="form-grid two"><label><span>Workflow code</span><input name="workflow_code" required></label><label><span>Entity type</span><input name="entity_type" value="project"></label><label><span>Entity ID</span><input name="entity_id" required></label><label><span>Current state code</span><input name="current_state_code" required></label><label><span>Country code</span><input name="country_code"></label><label><span>Tenant code</span><input name="tenant_code"></label><button class="btn btn-primary" type="submit">Create instance</button></form>`, submit: async fd=>request('/workflow/instances',{method:'POST',body:JSON.stringify({workflow_code:fd.get('workflow_code'),entity_type:fd.get('entity_type'),entity_id:fd.get('entity_id'),current_state_code:fd.get('current_state_code'),country_code:fd.get('country_code')||null,tenant_code:fd.get('tenant_code')||null})}), showResult:true }; }
function workflowActionForm(){ return { title:'Execute workflow action', eyebrow:'Workflow engine', formId:'workflowActionForm', body:`<form id="workflowActionForm" class="form-grid two"><label><span>Instance ID</span><input name="instance_id" type="number" required></label><label><span>Action code</span><input name="action_code" required></label><label><span>Actor</span><input name="actor" value="ui"></label><label><span>Actor role</span><input name="actor_role"></label><button class="btn btn-primary" type="submit">Execute action</button></form>`, submit: async fd=>request(`/workflow/instances/${fd.get('instance_id')}/actions`,{method:'POST',body:JSON.stringify({action_code:fd.get('action_code'),actor:fd.get('actor'),actor_role:fd.get('actor_role')||null})}), showResult:true }; }


function renderDashboard(){
  const notifications = itemsOf(state.datasets.notifications).slice(0,5);
  const projects = itemsOf(state.datasets.projects);
  const certifications = itemsOf(state.datasets.certifications);
  const atlas = state.datasets.atlas || {};
  setHero(
    'Structural truth cannot be negotiated. It must be proven.',
    'This dashboard now acts as an enterprise control plane: live portfolio posture, doctrine signals, certification state, and direct access to policy, workflow, governance, regulatory, and rollout controls.',
    [`${safeCount(projects)} projects`, `${safeCount(itemsOf(state.datasets.professionals))} professionals`, `${safeCount(itemsOf(state.datasets.tenders))} tenders`, `${safeCount(notifications.filter(n => !n.read))} unread alerts`]
  );
  setKpis([
    { label:'Total projects', value:num(state.summary?.total_projects ?? safeCount(projects)) },
    { label:'Average SHI', value:fmt(state.summary?.avg_shi) },
    { label:'Certified projects', value:num(safeCount(certifications)) },
    { label:'Portfolio value', value:money(state.summary?.total_project_value_usd, 'USD') }
  ]);

  el.workspace.innerHTML = `
    <div class="module-grid">
      <div class="stack">
        ${panel('Lighthouse portfolio', 'Projects', table(
          ['Project','Country','Phase','SHI','Status'],
          projects.slice(0,8).map(p => `<tr data-project="${p.uid}"><td><button class="link-btn" data-project-detail="${p.uid}">${p.name}</button><div class="muted small code">${p.uid}</div></td><td>${fmt(p.country)}</td><td>${fmt(p.phase)}</td><td>${fmt(p.shi)}</td><td>${badge(p.status)}</td></tr>`)
        ), `<button class="btn btn-sm" data-open-create="project">New project</button>`)}

        ${panel('Unread doctrine signals', 'Notifications', listTemplate(notifications, n => row(n.type || 'Notification', n.message, n.priority, !n.read ? `<button class="btn btn-sm btn-ghost" data-mark-read="${n.id}">Mark read</button>` : ''), 'No notifications yet.'), '')}
      </div>
      <div class="stack">
        ${panel('Institutional posture', 'Portfolio intelligence', cardStats([
          { label:'Countries active', value:num((atlas.countries || []).length) },
          { label:'Unread alerts', value:num(state.summary?.unread_notifications) },
          { label:'Tender pipeline', value:num(state.summary?.open_tenders) },
          { label:'Escrow released', value:money(atlas.payment_released_total || 0, 'USD') },
        ]), '')}
        ${panel('Certification threshold', 'SEAL™', listTemplate(certifications.slice(0,4), c => row(c.project_uid, `${fmt(c.type)} • SHI ${fmt(c.shi_composite)}`, c.status, `<button class="btn btn-sm btn-ghost" data-verify-seal="${c.project_uid}">Verify</button>`), 'No certifications yet.'), '')}
        ${panel('Enterprise control plane', 'Admin workflows', `<div class="actions-row">
          <button class="btn btn-sm" data-open-create="feature_flag">Feature flag</button>
          <button class="btn btn-sm btn-ghost" data-open-create="country_config">Country config</button>
          <button class="btn btn-sm btn-ghost" data-open-create="policy_rule">Policy rule</button>
          <button class="btn btn-sm btn-ghost" data-open-create="policy_eval">Policy eval</button>
          <button class="btn btn-sm btn-ghost" data-open-create="workflow_definition">Workflow def</button>
          <button class="btn btn-sm btn-ghost" data-open-create="workflow_instance">Workflow instance</button>
          <button class="btn btn-sm btn-ghost" data-open-create="workflow_action">Workflow action</button>
        </div><div class="note" style="margin-top:12px;">The original prototype now has first-class institutional controls for rollout, policy, workflow, regulatory authoring, governance decisions, funding, certification, and operational execution.</div>`, '')}
      </div>
    </div>`;
  bindDynamicActions();
}
