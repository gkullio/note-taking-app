const API = '/api/notes';
let notes = [];
let companies = [];
let contacts = [];
let accountManagers = [];
let contactSaveTimers = {};
let accountNotesSaveTimer;
let activeId = null;
let activeCompany = null;
let view = 'companies'; // 'companies' | 'notes'
let saveTimer = null;

// ── DOM refs ──
const noteList    = document.getElementById('note-list');
const emptyList   = document.getElementById('empty-list');
const emptyMsg    = document.getElementById('empty-list-msg');
const noteCount   = document.getElementById('note-count');
const editorBar   = document.getElementById('editor-toolbar');
const editorBody  = document.getElementById('editor-body');
const noNote      = document.getElementById('no-note');
const titleInput  = document.getElementById('title-input');
const contentInput= document.getElementById('content-input');
const acctMgrSelect = document.getElementById('acct-mgr-select');
const companyInput  = document.getElementById('company-input');
const dateInput     = document.getElementById('date-input');
const sfUrlInput    = document.getElementById('sf-url-input');
const sfUrlOpen     = document.getElementById('sf-url-open');
const saveStatus  = document.getElementById('save-status');
const searchInput = document.getElementById('search');
const overlay     = document.getElementById('modal-overlay');
const backBtn     = document.getElementById('btn-back');
const sidebarTitle = document.getElementById('sidebar-title');

// ── API helpers ──
async function apiFetch(url, method = 'GET', body) {
  const res = await fetch(url, {
    method,
    headers: body ? {'Content-Type':'application/json'} : {},
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
async function api(method, path, body) {
  return apiFetch(API + path, method, body);
}

// ── Sidebar nav ──
function updateSidebarHeader() {
  if (view === 'companies') {
    backBtn.style.display = 'none';
    sidebarTitle.textContent = 'Companies';
    searchInput.placeholder = 'Search companies…';
  } else {
    backBtn.style.display = 'inline';
    sidebarTitle.textContent = activeCompany || 'Notes';
    searchInput.placeholder = 'Search notes…';
  }
}

function goHome() {
  view = 'companies';
  activeCompany = null;
  searchInput.value = '';
  updateSidebarHeader();
  closeEditor();
  loadCompanies();
}

backBtn.onclick = goHome;
document.getElementById('btn-home').onclick = goHome;

// ── Companies ──
async function loadCompanies(q = '') {
  const url = q ? `/api/companies?q=${encodeURIComponent(q)}` : '/api/companies';
  companies = await apiFetch(url);
  renderCompanies();
}

function renderCompanies() {
  noteList.innerHTML = '';
  noteCount.textContent = companies.length;
  if (companies.length === 0) {
    emptyList.style.display = 'flex';
    emptyMsg.textContent = searchInput.value ? 'No matches found' : 'No companies yet';
    return;
  }
  emptyList.style.display = 'none';
  companies.forEach((c, i) => {
    const el = document.createElement('div');
    el.className = 'company-item';
    el.style.animationDelay = `${i * 0.03}s`;
    el.innerHTML = `
      <div class="company-item-name">${escHtml(c.company_name)}</div>
      <div class="company-item-meta">${c.note_count} note${c.note_count !== 1 ? 's' : ''} · ${formatDate(c.last_updated)}</div>
    `;
    el.onclick = () => openCompany(c.company_name);
    noteList.appendChild(el);
  });
}

async function openCompany(company) {
  view = 'notes';
  activeCompany = company;
  searchInput.value = '';
  updateSidebarHeader();
  await loadNotes();
}

// ── Load & render notes ──
async function loadNotes(q = '') {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (activeCompany !== null) params.set('company', activeCompany);
  const qs = params.toString();
  notes = await api('GET', qs ? `?${qs}` : '');
  renderList();
}

function formatDate(iso) {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return d.toLocaleDateString('en-US', {month:'short', day:'numeric'});
}

function renderList() {
  noteList.innerHTML = '';
  noteCount.textContent = notes.length;

  if (notes.length === 0) {
    emptyList.style.display = 'flex';
    emptyMsg.textContent = searchInput.value ? 'No matches found' : 'No notes yet';
  } else {
    emptyList.style.display = 'none';
  }

  notes.forEach((n, i) => {
    const el = document.createElement('div');
    el.className = 'note-item' + (n.id === activeId ? ' active' : '');
    el.style.animationDelay = `${i * 0.03}s`;
    const preview = n.content.replace(/\n/g,' ').slice(0, 60);
    el.innerHTML = `
      <div class="note-item-title">${escHtml(n.title || 'Untitled')}</div>
      <div class="note-item-meta">${formatDate(n.updated_at)}</div>
      ${preview ? `<div class="note-item-preview">${escHtml(preview)}</div>` : ''}
    `;
    el.onclick = () => openNote(n.id);
    noteList.appendChild(el);
  });
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Open note ──
function openNote(id) {
  activeId = id;
  const note = notes.find(n => n.id === id);
  if (!note) return;

  editorBar.style.display  = 'flex';
  editorBody.style.display = 'flex';
  noNote.style.display     = 'none';

  titleInput.value   = note.title;
  contentInput.value = note.content;
  populateAMSelect(note.account_manager || '');
  companyInput.value = note.company_name || '';
  dateInput.value    = note.date_last_contacted || '';
  sfUrlInput.value   = note.salesforce_url || '';
  updateSfLink();
  setSaveStatus('idle');
  renderList();
  autoResizeContent();
  contentInput.focus();
  contacts = [];
  renderContacts();
  loadContacts(note.company_name || '');
  loadAccountNotes(note.company_name || '');
}

function closeEditor() {
  activeId = null;
  contacts = [];
  const an = document.getElementById('account-notes-input');
  an.value = '';
  an.disabled = true;
  editorBar.style.display  = 'none';
  editorBody.style.display = 'none';
  noNote.style.display     = 'flex';
  renderList();
}

// ── Account Notes ──
async function loadAccountNotes(companyName) {
  const input = document.getElementById('account-notes-input');
  if (!companyName) {
    input.value = '';
    input.disabled = true;
    input.placeholder = 'Set a company name above to use account notes.';
    return;
  }
  input.disabled = false;
  input.placeholder = 'Notes about this account…';
  try {
    const data = await apiFetch(`/api/companies/${encodeURIComponent(companyName)}/account-notes`);
    input.value = data.content || '';
  } catch(e) {
    input.value = '';
  }
}

document.getElementById('account-notes-input').addEventListener('input', () => {
  clearTimeout(accountNotesSaveTimer);
  accountNotesSaveTimer = setTimeout(async () => {
    const company = companyInput.value.trim();
    if (!company) return;
    try {
      await apiFetch(`/api/companies/${encodeURIComponent(company)}/account-notes`, 'PUT', {
        content: document.getElementById('account-notes-input').value
      });
    } catch(e) {}
  }, 800);
});

// ── Contacts ──
async function loadContacts(companyName) {
  const noCompanyEl = document.getElementById('contacts-no-company');
  const addBtn = document.getElementById('btn-add-contact');
  if (!companyName) {
    contacts = [];
    renderContacts();
    noCompanyEl.style.display = 'block';
    addBtn.disabled = true;
    addBtn.style.opacity = '0.4';
    return;
  }
  noCompanyEl.style.display = 'none';
  addBtn.disabled = false;
  addBtn.style.opacity = '1';
  try {
    contacts = await apiFetch(`/api/companies/${encodeURIComponent(companyName)}/contacts`);
  } catch(e) {
    contacts = [];
  }
  renderContacts();
}

function renderContacts() {
  const tbody = document.getElementById('contacts-tbody');
  tbody.innerHTML = '';
  contacts.forEach(c => tbody.appendChild(makeContactRow(c)));
}

function makeContactRow(contact) {
  const row = document.createElement('div');
  row.className = 'contact-row';
  const defs = [
    { field: 'name',  placeholder: 'Name',  type: 'text'  },
    { field: 'email', placeholder: 'Email', type: 'email' },
    { field: 'team',  placeholder: 'Team',  type: 'text'  },
    { field: 'phone', placeholder: 'Phone', type: 'tel'   },
  ];
  defs.forEach(({ field, placeholder, type }) => {
    const inp = document.createElement('input');
    inp.type = type;
    inp.className = 'contact-cell-input';
    inp.value = contact[field] || '';
    inp.placeholder = placeholder;
    inp.spellcheck = false;
    inp.autocomplete = 'off';
    inp.addEventListener('input', () => {
      contact[field] = inp.value;
      clearTimeout(contactSaveTimers[contact.id]);
      contactSaveTimers[contact.id] = setTimeout(() => saveContact(contact), 600);
    });
    row.appendChild(inp);
  });
  const del = document.createElement('button');
  del.className = 'btn-del-contact';
  del.textContent = '×';
  del.title = 'Remove contact';
  del.onclick = async () => {
    await apiFetch(`/api/contacts/${contact.id}`, 'DELETE');
    contacts = contacts.filter(c => c.id !== contact.id);
    row.remove();
  };
  row.appendChild(del);
  return row;
}

async function saveContact(contact) {
  try {
    await apiFetch(`/api/contacts/${contact.id}`, 'PUT', {
      name: contact.name, email: contact.email,
      team: contact.team, phone: contact.phone
    });
  } catch(e) {}
}

document.getElementById('btn-add-contact').onclick = async () => {
  const company = companyInput.value.trim();
  if (!company) return;
  const contact = await apiFetch(`/api/companies/${encodeURIComponent(company)}/contacts`, 'POST', {
    name: '', email: '', team: '', phone: ''
  });
  contacts.push(contact);
  const row = makeContactRow(contact);
  document.getElementById('contacts-tbody').appendChild(row);
  row.querySelector('input').focus();
};

// ── Account Managers ──
async function loadAccountManagers() {
  try {
    accountManagers = await apiFetch('/api/account-managers');
    populateAMSelect();
  } catch(e) {}
}

function populateAMSelect(selectedValue) {
  const current = selectedValue !== undefined ? selectedValue : acctMgrSelect.value;
  acctMgrSelect.innerHTML = '<option value="">—</option>';
  accountManagers.forEach(am => {
    const opt = document.createElement('option');
    opt.value = am.name;
    opt.textContent = am.name;
    if (am.name === current) opt.selected = true;
    acctMgrSelect.appendChild(opt);
  });
}

document.getElementById('btn-add-am').onclick = () => {
  document.getElementById('am-add-row').style.display = 'flex';
  document.getElementById('am-add-input').focus();
};

document.getElementById('btn-am-cancel').onclick = () => {
  document.getElementById('am-add-row').style.display = 'none';
  document.getElementById('am-add-input').value = '';
};

document.getElementById('btn-am-confirm').onclick = async () => {
  const name = document.getElementById('am-add-input').value.trim();
  if (!name) return;
  try {
    const am = await apiFetch('/api/account-managers', 'POST', { name });
    accountManagers.push(am);
    accountManagers.sort((a, b) => a.name.localeCompare(b.name));
    populateAMSelect(am.name);
    document.getElementById('am-add-row').style.display = 'none';
    document.getElementById('am-add-input').value = '';
    scheduleSave();
  } catch(e) {
    // already exists — just close the row, the name is already in the list
    populateAMSelect(name);
    document.getElementById('am-add-row').style.display = 'none';
    document.getElementById('am-add-input').value = '';
  }
};

document.getElementById('am-add-input').addEventListener('keydown', e => {
  if (e.key === 'Enter')  document.getElementById('btn-am-confirm').click();
  if (e.key === 'Escape') document.getElementById('btn-am-cancel').click();
});

// ── Save status ──
function setSaveStatus(state, msg) {
  saveStatus.className = '';
  if (state === 'saving') {
    saveStatus.className = 'saving';
    saveStatus.textContent = 'saving…';
  } else if (state === 'saved') {
    saveStatus.className = 'saved';
    saveStatus.textContent = '✓ saved';
    setTimeout(() => { if (saveStatus.className === 'saved') setSaveStatus('idle'); }, 2000);
  } else {
    saveStatus.textContent = msg || '—';
  }
}

// ── Auto-save ──
function scheduleSave() {
  setSaveStatus('saving');
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveActive, 800);
}

async function saveActive() {
  if (!activeId) return;
  try {
    const updated = await api('PUT', `/${activeId}`, {
      title: titleInput.value || 'Untitled',
      content: contentInput.value,
      account_manager: acctMgrSelect.value,
      company_name: companyInput.value,
      date_last_contacted: dateInput.value,
      salesforce_url: sfUrlInput.value
    });
    const idx = notes.findIndex(n => n.id === activeId);
    if (idx !== -1) notes[idx] = updated;
    setSaveStatus('saved');
    renderList();
  } catch(e) {
    setSaveStatus('idle', '⚠ save failed');
  }
}

// ── Auto-resize ──
function autoResizeContent() {
  contentInput.style.height = 'auto';
  contentInput.style.height = contentInput.scrollHeight + 'px';
}

titleInput.addEventListener('input', scheduleSave);
contentInput.addEventListener('input', () => { autoResizeContent(); scheduleSave(); });
function updateSfLink() {
  const url = sfUrlInput.value.trim();
  if (url) {
    sfUrlOpen.href = /^https?:\/\//i.test(url) ? url : 'https://' + url;
    sfUrlOpen.classList.add('show');
  } else {
    sfUrlOpen.href = '#';
    sfUrlOpen.classList.remove('show');
  }
}

sfUrlInput.addEventListener('input', () => { updateSfLink(); scheduleSave(); });
acctMgrSelect.addEventListener('change', scheduleSave);
let contactCompanyTimer;
companyInput.addEventListener('input', () => {
  scheduleSave();
  clearTimeout(contactCompanyTimer);
  contactCompanyTimer = setTimeout(() => {
    const c = companyInput.value.trim();
    loadContacts(c);
    loadAccountNotes(c);
  }, 1000);
});
dateInput.addEventListener('change', scheduleSave);

// ── New note ──
document.getElementById('btn-new').onclick = async () => {
  const payload = { title: 'Untitled', content: '' };
  if (view === 'notes' && activeCompany) payload.company_name = activeCompany;
  const note = await api('POST', '', payload);
  if (view === 'companies') {
    notes = [note];
  } else {
    notes.unshift(note);
    renderList();
  }
  openNote(note.id);
  titleInput.select();
};

// ── Search + company dropdown ──
const searchDropdown = document.getElementById('search-dropdown');
let searchTimer;
let dropdownTimer;

async function refreshDropdown(q) {
  try {
    const url = q ? `/api/companies?q=${encodeURIComponent(q)}` : '/api/companies';
    const cos = await apiFetch(url);
    searchDropdown.innerHTML = '';
    if (cos.length === 0) {
      searchDropdown.innerHTML = '<div class="dd-empty">No companies found</div>';
    } else {
      cos.forEach(c => {
        const item = document.createElement('div');
        item.className = 'dd-item';
        item.innerHTML = `<span class="dd-name">${escHtml(c.company_name)}</span>
          <span class="dd-count">${c.note_count} note${c.note_count !== 1 ? 's' : ''}</span>`;
        item.onmousedown = e => {
          e.preventDefault();
          searchInput.value = '';
          searchDropdown.classList.remove('show');
          openCompany(c.company_name);
        };
        searchDropdown.appendChild(item);
      });
    }
    searchDropdown.classList.add('show');
  } catch(e) {}
}

searchInput.addEventListener('focus', () => { if (view === 'companies') refreshDropdown(searchInput.value.trim()); });
searchInput.addEventListener('blur',  () => setTimeout(() => searchDropdown.classList.remove('show'), 150));
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  clearTimeout(dropdownTimer);
  const q = searchInput.value.trim();
  searchTimer   = setTimeout(() => { if (view === 'companies') loadCompanies(q); else loadNotes(q); }, 200);
  if (view === 'companies') dropdownTimer = setTimeout(() => refreshDropdown(q), 150);
});

// ── Delete ──
document.getElementById('btn-delete').onclick = () => overlay.classList.add('show');
document.getElementById('modal-cancel').onclick = () => overlay.classList.remove('show');
document.getElementById('modal-confirm').onclick = async () => {
  overlay.classList.remove('show');
  if (!activeId) return;
  await api('DELETE', `/${activeId}`);
  notes = notes.filter(n => n.id !== activeId);
  closeEditor();
};
overlay.addEventListener('click', e => { if (e.target === overlay) overlay.classList.remove('show'); });

// ── Keyboard shortcuts ──
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
    e.preventDefault();
    document.getElementById('btn-new').click();
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
    e.preventDefault();
    searchInput.focus();
    searchInput.select();
  }
  if (e.key === 'Escape') overlay.classList.remove('show');
});

// ── Init ──
updateSidebarHeader();
loadAccountManagers();
loadCompanies();
noNote.style.display = 'flex';
