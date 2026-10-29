import { renderIcons } from './icons.js';

const PLACES = ['کاشان', 'تبریز', 'اصفهان', 'شیراز', 'یزد', 'مشهد', 'تهران', 'کرمان', 'قم', 'رشت', 'کیش', 'قشم'];
const PRESET_TLDS = ['ir', 'com', 'net', 'org', 'shop', 'store', 'co', 'io', 'app', 'site'];
const DRAFT_KEY = 'netnama-name-draft';
const ROLES = ['name', 'keyword', 'place', 'custom'];

export function mountNameStudio({t, api, toast}) {
  if (document.body.dataset.page !== 'domain_names') return () => {};
  const $ = (id) => document.getElementById(id);
  const state = {step: 1, tokens: [], gender: '', tlds: ['ir', 'com'], joined: true, hyphen: true, domains: [], results: [], total: 0, count: 0, namePage: 1, pages: 1, pageSize: 48};
  let nextId = 1;
  let builtFrom = '';
  let searchTimer;
  let searchSequence = 0;
  let building = false;
  let checking = false;
  let checkJob = null;
  let checkTimer;
  let pollSequence = 0;
  let checkResults = new Map();
  try {
    const saved = JSON.parse(sessionStorage.getItem(DRAFT_KEY) || 'null');
    if (saved && Array.isArray(saved.tokens)) {
      state.tokens = saved.tokens.filter(token => token && typeof token.fa === 'string').slice(0, 8).map((token, index) => ({...token, id: index + 1, fa: token.fa.slice(0, 40), latin: typeof token.latin === 'string' ? token.latin.slice(0, 63) : '', role: ROLES.includes(token.role) ? token.role : 'keyword'}));
      state.step = Math.min(Math.max(Math.floor(Number(saved.step)) || 1, 1), 4);
      state.gender = ['', 'm', 'f', 'b'].includes(saved.gender) ? saved.gender : '';
      state.tlds = Array.isArray(saved.tlds) && saved.tlds.length ? saved.tlds.filter(tld => typeof tld === 'string' && /^[a-z0-9.-]{1,24}$/.test(tld)).slice(0, 12) : state.tlds;
      state.joined = saved.joined !== false;
      state.hyphen = saved.hyphen !== false;
      state.domains = Array.isArray(saved.domains) ? saved.domains.filter(item => item && typeof item.domain === 'string').slice(0, 400) : [];
      nextId = state.tokens.reduce((max, token) => Math.max(max, Number(token.id) || 0), 0) + 1;
      builtFrom = saved.builtFrom || '';
    }
  } catch { /* keep the empty draft */ }

  const persist = () => {
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify({...state, results: undefined, builtFrom}));
    } catch { /* the draft is only a convenience */ }
  };
  const signature = () => JSON.stringify({tokens: state.tokens.map(({fa, latin, role}) => ({fa, latin, role})), tlds: state.tlds, joined: state.joined, hyphen: state.hyphen});

  function field(value, label) {
    const input = document.createElement('input');
    input.value = value || '';
    input.maxLength = 40;
    input.autocomplete = 'off';
    input.setAttribute('aria-label', label);
    return input;
  }
  function removeToken(id) {
    state.tokens = state.tokens.filter(token => token.id !== id);
    builtFrom = '';
    persist();
    renderDynamic();
  }
  async function addText(text, role) {
    const trimmed = text.trim();
    if (!trimmed) {toast(t('empty_input')); return;}
    if (state.tokens.length >= 8) {toast(t('too_many_inputs')); return;}
    let info;
    try {info = await api('/api/names/inspect', {text: trimmed});}
    catch (error) {toast(error.message); return;}
    if (state.tokens.length >= 8) {toast(t('too_many_inputs')); return false;}
    const chosen = role || (info.role === 'name' ? 'keyword' : info.role);
    if (state.tokens.some(token => token.fa === info.fa && token.role === chosen)) {toast(t('studio_duplicate')); return;}
    state.tokens.push({id: nextId++, fa: info.fa, latin: info.latin, role: chosen, gender: info.gender, latinTouched: false});
    builtFrom = '';
    persist();
    renderDynamic();
    return true;
  }
  function tokenRow(token, {roles = false, move = false} = {}) {
    const row = document.createElement('div');
    row.className = roles ? 'token-row' : 'token-row compact';
    const persian = field(token.fa, t('studio_persian'));
    const latin = field(token.latin, t('studio_latin'));
    latin.dir = 'ltr';
    latin.maxLength = 63;
    persian.addEventListener('input', () => {token.fa = persian.value; builtFrom = ''; persist(); renderSummary();});
    latin.addEventListener('input', () => {token.latin = latin.value.trim().toLowerCase(); token.latinTouched = true; builtFrom = ''; persist(); renderSummary();});
    persian.addEventListener('change', async () => {
      if (!persian.value.trim() || token.latinTouched) return;
      try {
        const info = await api('/api/names/inspect', {text: persian.value.trim()});
        token.fa = info.fa;
        token.latin = info.latin;
        token.gender = info.gender;
        if (!roles) token.role = info.role;
        persian.value = info.fa;
        latin.value = info.latin;
        builtFrom = '';
        persist();
        renderDynamic();
      } catch (error) {toast(error.message);}
    });
    row.append(persian, latin);
    if (roles) {
      const select = document.createElement('select');
      select.setAttribute('aria-label', t('studio_role'));
      for (const role of ROLES) {
        const option = document.createElement('option');
        option.value = role;
        option.textContent = t(`studio_role_${role}`);
        option.selected = token.role === role;
        select.append(option);
      }
      select.addEventListener('change', () => {token.role = select.value; builtFrom = ''; persist(); renderSummary();});
      row.append(select);
    }
    const actions = document.createElement('div');
    actions.className = 'token-actions';
    if (move) {
      const index = state.tokens.findIndex(item => item.id === token.id);
      actions.append(iconButton('chevron-up', t('studio_move_up'), index === 0, () => moveToken(index, -1)));
      actions.append(iconButton('chevron-down', t('studio_move_down'), index === state.tokens.length - 1, () => moveToken(index, 1)));
    }
    actions.append(iconButton('trash-2', t('studio_remove'), false, () => removeToken(token.id)));
    row.append(actions);
    return row;
  }
  function iconButton(icon, label, disabled, action) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'icon-button';
    button.disabled = disabled;
    button.setAttribute('aria-label', label);
    const glyph = document.createElement('i');
    glyph.dataset.icon = icon;
    glyph.setAttribute('aria-hidden', 'true');
    button.append(glyph);
    button.addEventListener('click', action);
    return button;
  }
  function moveToken(index, delta) {
    const next = index + delta;
    if (next < 0 || next >= state.tokens.length) return;
    const [item] = state.tokens.splice(index, 1);
    state.tokens.splice(next, 0, item);
    builtFrom = '';
    persist();
    renderDynamic();
  }
  function renderSummary() {
    const box = $('token-summary');
    box.replaceChildren();
    if (state.domains.length && state.tokens.length && signature() !== builtFrom) {
      const notice = document.createElement('p');
      notice.className = 'studio-stale small';
      notice.textContent = t('studio_stale');
      box.append(notice);
    }
    for (const token of state.tokens) {
      const chip = document.createElement('span');
      chip.className = 'summary-chip';
      chip.textContent = token.latin ? `${token.fa} · ${token.latin}` : token.fa;
      box.append(chip);
    }
  }
  function renderWords() {
    const box = $('word-list');
    box.replaceChildren();
    for (const token of state.tokens.filter(token => token.role !== 'name')) box.append(tokenRow(token));
  }
  function renderSelectedNames() {
    const box = $('name-selected');
    box.replaceChildren();
    for (const token of state.tokens.filter(token => token.role === 'name')) box.append(tokenRow(token));
  }
  function renderResults() {
    const box = $('name-results');
    box.replaceChildren();
    const query = $('name-query').value.trim();
    const from = state.total ? (state.namePage - 1) * state.pageSize + 1 : 0;
    const to = Math.min(state.namePage * state.pageSize, state.total);
    $('name-count').textContent = state.total ? `${from}–${to} / ${state.total}` : '0';
    $('name-pages').textContent = `/ ${state.pages || 1}`;
    $('name-page-input').max = String(state.pages || 1);
    if (document.activeElement !== $('name-page-input')) $('name-page-input').value = String(state.namePage || 1);
    $('names-prev').disabled = state.namePage <= 1;
    $('names-next').disabled = state.namePage >= (state.pages || 1);
    for (const item of state.results) {
      const selected = state.tokens.some(token => token.role === 'name' && token.fa === item.name);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'name-hit';
      button.setAttribute('aria-pressed', String(selected));
      const title = document.createElement('strong');
      title.textContent = item.name;
      const latin = document.createElement('bdi');
      latin.dir = 'ltr';
      latin.textContent = item.latin;
      const gender = document.createElement('small');
      gender.textContent = item.gender ? t(`gender_${item.gender}`) : '';
      button.append(title, latin, gender);
      button.addEventListener('click', () => {
        if (selected) removeToken(state.tokens.find(token => token.role === 'name' && token.fa === item.name).id);
        else if (state.tokens.length >= 8) toast(t('too_many_inputs'));
        else if (state.tokens.some(token => token.fa === item.name && token.role === 'name')) toast(t('studio_duplicate'));
        else {
          state.tokens.push({id: nextId++, fa: item.name, latin: item.latin, role: 'name', gender: item.gender, latinTouched: false});
          builtFrom = '';
          persist();
          renderDynamic();
        }
      });
      box.append(button);
    }
    const showEmpty = Boolean(query) && state.total === 0;
    $('name-empty').hidden = !showEmpty;
    $('add-custom-name').hidden = !showEmpty;
  }
  function renderTokens() {
    const box = $('token-list');
    box.replaceChildren();
    for (const token of state.tokens) box.append(tokenRow(token, {roles: true, move: true}));
  }
  function renderTlds() {
    const box = $('tld-list');
    box.replaceChildren();
    const extras = state.tlds.filter(tld => !PRESET_TLDS.includes(tld));
    for (const tld of [...PRESET_TLDS, ...extras]) {
      const label = document.createElement('label');
      label.className = 'tld-option';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.checked = state.tlds.includes(tld);
      input.addEventListener('change', () => {
        if (input.checked && state.tlds.length >= 12) {input.checked = false; toast(t('studio_tld_limit')); return;}
        state.tlds = input.checked ? [...state.tlds, tld] : state.tlds.filter(item => item !== tld);
        builtFrom = '';
        persist();
        renderSummary();
        if (!PRESET_TLDS.includes(tld)) renderTlds();
      });
      const text = document.createElement('span');
      text.dir = 'ltr';
      text.textContent = `.${tld}`;
      label.append(input, text);
      box.append(label);
    }
  }
  function renderDomains({preserveEditing = false} = {}) {
    if (preserveEditing && document.activeElement?.matches('#domain-list input[type=text]')) {
      updateDomainCount(visibleDomains().length);
      return;
    }
    const box = $('domain-list');
    box.replaceChildren();
    renderSummary();
    $('domain-empty').hidden = state.domains.length > 0;
    const allOn = state.domains.length > 0 && state.domains.every(item => item.selected);
    $('select-domains').textContent = t(allOn ? 'studio_deselect_all' : 'studio_select_all');
    const visible = visibleDomains();
    $('domain-no-match').hidden = !state.domains.length || visible.length > 0;
    updateDomainCount(visible.length);
    for (const item of visible) {
      const row = document.createElement('div');
      row.className = 'domain-row';
      const check = document.createElement('input');
      check.type = 'checkbox';
      check.checked = item.selected !== false;
      check.setAttribute('aria-label', item.domain);
      check.addEventListener('change', () => {
        item.selected = check.checked;
        persist();
        updateDomainCount(visibleDomains().length);
        const allOn = state.domains.length > 0 && state.domains.every(entry => entry.selected !== false);
        $('select-domains').textContent = t(allOn ? 'studio_deselect_all' : 'studio_select_all');
      });
      const input = document.createElement('input');
      input.type = 'text';
      input.dir = 'ltr';
      input.maxLength = 253;
      input.value = item.domain;
      input.spellcheck = false;
      input.setAttribute('aria-label', t('studio_step_address'));
      input.addEventListener('change', () => {item.domain = input.value.trim().toLowerCase(); persist(); renderDomains();});
      const kind = document.createElement('span');
      kind.className = 'badge neutral';
      kind.textContent = t(`kind_${item.kind || 'full'}`);
      const persian = document.createElement('span');
      persian.className = 'small muted';
      persian.textContent = item.persian || '';
      const favorite = document.createElement('button');
      favorite.type = 'button';
      favorite.className = 'favorite-button';
      favorite.textContent = item.favorite ? '★' : '☆';
      favorite.setAttribute('aria-label', `${t('studio_favorite')}: ${item.domain}`);
      favorite.setAttribute('aria-pressed', String(Boolean(item.favorite)));
      favorite.addEventListener('click', () => {item.favorite = !item.favorite; persist(); renderDomains();});
      const result = checkResults.get(item.domain);
      const detail = document.createElement('div');
      detail.className = 'domain-detail';
      const badge = document.createElement('span');
      badge.className = `badge ${result?.status === 'likely_available' ? 'success' : result?.status === 'registered' ? 'warning' : 'neutral'}`;
      badge.textContent = result ? t(result.status) : t('studio_unchecked');
      detail.append(badge);
      if (result) {
        const reason = document.createElement('small');
        const key = `reason_${result.reason_code}`;
        reason.textContent = t(key) === key ? t(result.status) : t(key);
        detail.append(reason);
        const time = document.createElement('small');
        time.textContent = result.checked_at || '';
        detail.append(time);
      }
      row.append(check, input, favorite, kind, persian, detail);
      box.append(row);
    }
  }
  function renderSteps() {
    for (const button of document.querySelectorAll('.name-studio .step')) {
      button.setAttribute('aria-current', Number(button.dataset.step) === state.step ? 'step' : 'false');
    }
    for (let number = 1; number <= 4; number += 1) $(`studio-${number}`).hidden = number !== state.step;
    $('studio-back').hidden = state.step === 1;
    $('studio-next').hidden = state.step === 4;
    for (const button of document.querySelectorAll('#gender-filters button')) button.setAttribute('aria-pressed', String(button.dataset.gender === state.gender));
    $('style-joined').checked = state.joined;
    $('style-hyphen').checked = state.hyphen;
    $('check-domains').disabled = checking || building || !selectedDomains().length;
    $('build-domains').disabled = checking || building;
    $('cancel-check').hidden = !checking || !checkJob;
    $('studio-next').textContent = `${t('studio_next')}: ${t(state.step === 1 ? 'studio_step_names' : state.step === 2 ? 'studio_step_latin' : 'studio_step_address')}`;
    $('word-input').placeholder = t('studio_word_placeholder');
    $('name-query').placeholder = t('studio_name_placeholder');
  }
  function renderDynamic() {
    renderSummary();
    renderWords();
    renderSelectedNames();
    renderResults();
    renderTokens();
    renderTlds();
    renderDomains();
    renderSteps();
    renderIcons();
  }
  async function searchNames(page = 1) {
    const query = $('name-query').value.trim();
    const sequence = ++searchSequence;
    $('name-results').setAttribute('aria-busy', 'true');
    try {
      const data = await api(`/api/names?q=${encodeURIComponent(query)}&gender=${state.gender}&limit=48&page=${page}`);
      if (sequence !== searchSequence) return;
      state.results = data.items;
      state.total = data.total;
      state.count = data.count;
      state.namePage = data.page;
      state.pages = data.pages;
      state.pageSize = data.page_size;
      renderResults();
    } catch (error) {if (sequence === searchSequence) toast(error.message);}
    finally {if (sequence === searchSequence) $('name-results').setAttribute('aria-busy', 'false');}
  }
  async function build() {
    if (building || checking) return;
    if (!state.tokens.length) {toast(t('studio_need_token')); return;}
    if (state.tokens.some(token => !token.latin.trim())) {toast(t('studio_latin_missing')); return;}
    if (!state.tlds.length) {toast(t('studio_need_tld')); return;}
    if (!state.joined && !state.hyphen) {toast(t('invalid_options')); return;}
    if (state.tokens.some(token => !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(token.latin))) {toast(t('studio_latin_invalid')); return;}
    const requestedSignature = signature();
    building = true;
    renderSteps();
    try {
      const result = await api('/api/names/compose', {
        tokens: state.tokens.map(({fa, latin, role}) => ({fa, latin, role})),
        tlds: state.tlds,
        styles: [state.joined ? 'joined' : '', state.hyphen ? 'hyphen' : ''].filter(Boolean),
      });
      if (signature() !== requestedSignature) {toast(t('studio_stale')); return;}
      result.tokens.forEach((token, index) => {
        if (!state.tokens[index]) return;
        state.tokens[index].fa = token.fa;
        state.tokens[index].latin = token.latin;
        state.tokens[index].role = token.role;
      });
      const favorites = new Set(state.domains.filter(item => item.favorite).map(item => item.domain));
      const kept = state.domains.filter(item => item.favorite && !result.domains.some(next => next.domain === item.domain));
      state.domains = [...kept, ...result.domains.map(item => ({...item, selected: true, favorite: favorites.has(item.domain)}))].slice(0, 400);
      builtFrom = signature();
      persist();
      renderDynamic();
      toast(`${t('studio_built')} ${state.domains.length}`);
    } catch (error) {toast(error.message);}
    finally {building = false; renderSteps();}
  }
  function selectedDomains() {
    return state.domains.map(item => item.domain.trim()).filter((domain, index) => state.domains[index].selected !== false && domain);
  }
  function show(step) {
    if (step === 3 && step > state.step) {
      if (!state.tokens.length) {toast(t('studio_need_token')); return;}
      if (state.tokens.some(token => !token.latin.trim())) {toast(t('studio_latin_missing')); return;}
    }
    if (building) return;
    state.step = step;
    persist();
    renderSteps();
    $(`studio-${step}`).focus();
    if (step === 2 && !state.results.length) searchNames();
    if (step === 4 && state.tokens.length && signature() !== builtFrom) build();
  }

  $('word-add').addEventListener('click', async () => {
    const value = $('word-input').value;
    $('word-add').disabled = true;
    try {if (await addText(value) && $('word-input').value === value) $('word-input').value = '';}
    finally {$('word-add').disabled = false; $('word-input').focus();}
  });
  $('word-input').addEventListener('keydown', event => {if (event.key === 'Enter') {event.preventDefault(); $('word-add').click();}});
  for (const place of PLACES) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'place-chip';
    button.textContent = place;
    button.addEventListener('click', () => addText(place, 'place'));
    $('place-suggestions').append(button);
  }
  $('name-query').addEventListener('input', () => {++searchSequence; clearTimeout(searchTimer); searchTimer = setTimeout(() => searchNames(1), 200);});
  $('name-query').addEventListener('keydown', event => {if (event.key === 'Enter') {event.preventDefault(); $('add-custom-name').hidden ? null : $('add-custom-name').click();}});
  for (const button of document.querySelectorAll('#gender-filters button')) {
    button.addEventListener('click', () => {state.gender = button.dataset.gender; persist(); renderSteps(); searchNames(1);});
  }
  $('add-custom-name').addEventListener('click', () => addText($('name-query').value, 'name'));
  $('names-prev').addEventListener('click', () => {if (state.namePage > 1) searchNames(state.namePage - 1);});
  $('names-next').addEventListener('click', () => {if (state.namePage < state.pages) searchNames(state.namePage + 1);});
  $('name-page-input').addEventListener('change', () => {
    const page = Number($('name-page-input').value);
    if (!Number.isInteger(page) || page < 1) {$('name-page-input').value = String(state.namePage); return;}
    searchNames(page);
  });
  $('style-joined').addEventListener('change', () => {state.joined = $('style-joined').checked; builtFrom = ''; persist(); renderSummary();});
  $('style-hyphen').addEventListener('change', () => {state.hyphen = $('style-hyphen').checked; builtFrom = ''; persist(); renderSummary();});
  $('tld-add').addEventListener('click', () => {
    const tld = $('tld-input').value.trim().toLowerCase().replace(/^\.+/, '');
    if (!/^[a-z0-9](?:[a-z0-9-]{0,22}[a-z0-9])?(?:\.[a-z]{2,12})?$/.test(tld)) {toast(t('studio_invalid_tld')); return;}
    if (!state.tlds.includes(tld) && state.tlds.length >= 12) {toast(t('studio_tld_limit')); return;}
    if (!state.tlds.includes(tld)) state.tlds.push(tld);
    $('tld-input').value = '';
    builtFrom = '';
    persist();
    renderTlds();
    renderSummary();
  });
  $('tld-input').addEventListener('keydown', event => {if (event.key === 'Enter') {event.preventDefault(); $('tld-add').click();}});
  $('build-domains').addEventListener('click', build);
  $('select-domains').addEventListener('click', () => {
    const allOn = state.domains.length > 0 && state.domains.every(item => item.selected !== false);
    for (const item of state.domains) item.selected = !allOn;
    persist();
    renderDomains();
  });
  $('copy-domains').addEventListener('click', async () => {
    const text = [...new Set(selectedDomains())].join('\n');
    if (!text) {toast(t('studio_need_domain')); return;}
    try {await navigator.clipboard.writeText(text); toast(t('copied'));}
    catch {toast(t('network_error'));}
  });
  $('use-domains').addEventListener('click', () => {
    const text = [...new Set(selectedDomains())].join('\n');
    if (!text) {toast(t('studio_need_domain')); return;}
    try {sessionStorage.setItem('netnama-domain-import', text);} catch {toast(t('network_error')); return;}
    location.assign('/tools/domain_batch');
  });
  $('studio-direct-jump').addEventListener('click', () => {show(4); $('direct-domain').focus();});
  $('studio-back').addEventListener('click', () => show(state.step - 1));
  $('studio-next').addEventListener('click', () => show(state.step + 1));
  for (const button of document.querySelectorAll('.name-studio .step')) {
    button.addEventListener('click', () => show(Number(button.dataset.step)));
  }
  function visibleDomains() {
    const query = $('domain-filter').value.trim().toLowerCase();
    const status = $('domain-status').value;
    const items = state.domains.filter(item => {
      const result = checkResults.get(item.domain);
      return item.domain.includes(query) && (!$('favorites-only').checked || item.favorite) &&
        (status === 'all' || (status === 'unchecked' ? !result : status === 'unresolved' ? result && !['registered', 'likely_available'].includes(result.status) : result?.status === status));
    });
    if ($('domain-sort').value === 'short') items.sort((a,b) => a.domain.length - b.domain.length);
    if ($('domain-sort').value === 'alpha') items.sort((a,b) => a.domain.localeCompare(b.domain));
    return items;
  }
  function updateDomainCount(visible) {
    $('domain-count').textContent = `${visible} / ${state.domains.length} ${t('studio_visible')} · ${selectedDomains().length} ${t('studio_selected')}`;
    $('check-domains').disabled = checking || building || !selectedDomains().length;
  }
  function applyCheck(job) {
    checkJob = job.job_id;
    for (const result of job.results) checkResults.set(result.ascii || result.input, result);
    checking = !['completed', 'partial', 'failed', 'cancelled'].includes(job.status);
    $('check-progress').textContent = `${t(checking ? 'studio_check_wait' : 'studio_check_done')} · ${job.summary.completed} / ${job.summary.total} · ${t(job.status)}`;
    $('check-meter').hidden = false;
    $('check-meter').max = job.summary.total || 1;
    $('check-meter').value = job.summary.completed;
    renderDomains({preserveEditing: true});
    renderSteps();
    if (checking) checkTimer = setTimeout(pollCheck, 1200);
  }
  async function pollCheck() {
    const sequence = ++pollSequence;
    try {
      const job = await api(`/api/jobs/${checkJob}`);
      if (sequence !== pollSequence) return;
      applyCheck(job);
    }
    catch (error) {
      if (sequence !== pollSequence) return;
      checking = false;
      $('check-progress').textContent = t('studio_check_interrupted');
      toast(error.message);
      renderSteps();
    }
  }
  $('check-domains').addEventListener('click', async () => {
    if (checking || building) return;
    const domains = [...new Set(selectedDomains())];
    if (!domains.length) {toast(t('studio_need_domain')); return;}
    if (state.tokens.length && signature() !== builtFrom) {toast(t('studio_stale_check')); return;}
    checking = true;
    checkJob = null;
    ++pollSequence;
    renderSteps();
    clearTimeout(checkTimer);
    try {
      const job = await api('/api/jobs', {tool: 'domain_batch', text: domains.join('\n'), options: {force_fresh: $('fresh-check').checked}});
      try {sessionStorage.setItem('netnama-studio-job', job.job_id);} catch { /* optional restore */ }
      applyCheck(job);
    } catch (error) {checking = false; renderSteps(); toast(error.message);}
  });
  $('cancel-check').addEventListener('click', async () => {
    try {await api(`/api/jobs/${checkJob}/cancel`, {}); clearTimeout(checkTimer); await pollCheck();}
    catch (error) {toast(error.message);}
  });
  for (const id of ['domain-filter', 'domain-status', 'favorites-only', 'domain-sort']) $(id).addEventListener(id === 'domain-filter' ? 'input' : 'change', renderDomains);
  $('direct-add').addEventListener('click', async () => {
    const value = $('direct-domain').value.trim();
    if (!value) {toast(t('studio_need_domain')); return;}
    try {
      const result = await api('/api/domain/normalize', {target: value});
      if (result.ascii !== result.registrable) {toast(t('reason_subdomain')); return;}
      if (state.domains.some(item => item.domain === result.ascii)) {toast(t('studio_duplicate')); return;}
      if (state.domains.length >= 400) {toast(t('too_many_inputs')); return;}
      state.domains.push({domain: result.ascii, selected: true, kind: 'full'});
      $('direct-domain').value = '';
      persist(); renderDomains();
    } catch (error) {toast(error.message);}
  });
  $('direct-domain').addEventListener('keydown', event => {if (event.key === 'Enter') {event.preventDefault(); $('direct-add').click();}});
  renderDynamic();
  try {checkJob = sessionStorage.getItem('netnama-studio-job'); if (checkJob) {checking = true; renderSteps(); pollCheck();}} catch { /* optional restore */ }
  if (state.step === 2) searchNames();
  if (state.step === 4 && state.tokens.length && signature() !== builtFrom) build();
  return renderDynamic;
}
