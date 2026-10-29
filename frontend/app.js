import { renderIcons } from './icons.js';
import { Terminal } from './terminal.js';
const $ = (id) => document.getElementById(id);
const catalogs = JSON.parse($('catalogs').textContent);
let locale = document.documentElement.lang;
const t = key => catalogs[locale][key] || key;
const page = document.body.dataset.page;
let current = null, source = null, poll = null, capabilities = null, resourceData = null;
let lastEvent = 0;
let toastTimer;
const safeGet = (key, fallback) => {try {return localStorage.getItem(key) || fallback;} catch {return fallback;}};
const safeSet = (key, value) => {try {localStorage.setItem(key, value);} catch {}};
function toast(text) {$('toast').textContent = text; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 5500);}
function translate() {
  document.documentElement.lang = locale; document.documentElement.dir = locale === 'fa' ? 'rtl' : 'ltr';
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll('[data-aria]')) el.setAttribute('aria-label', t(el.dataset.aria));
  for (const el of document.querySelectorAll('[data-title]')) el.title = t(el.dataset.title);
  $('locale-label').textContent = locale === 'fa' ? 'EN' : 'فا';
  document.title = `${t('brand')} · ${t(page)}`;
  if(current) renderJob();
  if(capabilities) renderCapabilities();
  if(resourceData) renderResources();
}
$('locale-toggle')?.addEventListener('click', () => {locale = locale === 'fa' ? 'en' : 'fa'; safeSet('locale', locale); translate();});
const themeSelect = $('theme-select'); themeSelect.value = safeGet('theme', 'system');
function applyTheme() {const pref = themeSelect.value; document.documentElement.dataset.theme = pref === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : pref;}
themeSelect.addEventListener('change', () => {safeSet('theme', themeSelect.value); applyTheme();});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);
async function api(url, data) {
  const response = await fetch(url, {method:data === undefined ? 'GET' : 'POST', headers:{'X-CSRFToken':document.querySelector('meta[name=csrf-token]').content, 'X-NetNama-Locale':locale, ...(data instanceof FormData ? {} : {'Content-Type':'application/json'})}, body:data === undefined ? undefined : data instanceof FormData ? data : JSON.stringify(data)});
  let result;
  try {result = await response.json();} catch {throw new Error(t('network_error'));}
  if(!response.ok) {if(response.status === 401) toast(t('authentication_required')); throw new Error(t(Object.hasOwn(catalogs[locale],result.error) ? result.error : 'reason_fallback'));}
  return result;
}
let previousFocus;
function drawer(open) {
  const sidebar = $('sidebar'); if(!sidebar) return;
  sidebar.classList.toggle('open', open);sidebar.inert=!open && matchMedia('(max-width:850px)').matches;document.querySelector('.main-shell').inert=open;document.body.classList.toggle('drawer-active',open); $('drawer-backdrop').hidden = !open; $('drawer-open').setAttribute('aria-expanded', String(open));
  if(open) {previousFocus = document.activeElement; sidebar.setAttribute('role', 'dialog'); sidebar.setAttribute('aria-modal', 'true'); $('drawer-close').focus();}
  else {sidebar.removeAttribute('role'); sidebar.removeAttribute('aria-modal'); previousFocus?.focus();}
}
$('drawer-open')?.addEventListener('click', () => drawer(true)); $('drawer-close')?.addEventListener('click', () => drawer(false)); $('drawer-backdrop')?.addEventListener('click', () => drawer(false));
document.addEventListener('keydown', e => {
  if(!$('sidebar')?.classList.contains('open')) return;
  if(e.key === 'Escape') drawer(false);
  if(e.key === 'Tab') {const nodes = [...$('sidebar').querySelectorAll('a,button')].filter(el => el.getClientRects().length); const first=nodes[0], last=nodes.at(-1); if(e.shiftKey && document.activeElement===first) {e.preventDefault();last.focus();} else if(!e.shiftKey && document.activeElement===last) {e.preventDefault();first.focus();}}
});
$('login-form')?.addEventListener('submit', () => {const button=$('login-form').querySelector('button');button.disabled=true;button.classList.add('busy');});
const terminal = new Terminal($('terminal'), () => {if($('truncation')) $('truncation').hidden = false;});
$('copy-terminal')?.addEventListener('click', async () => {try {await navigator.clipboard.writeText($('terminal').textContent);toast(t('copied'));} catch {toast(t('network_error'));}});
$('clear-terminal')?.addEventListener('click', () => {terminal.clear();toast(t('clear_help'));});
$('wrap-terminal')?.addEventListener('click', e => {const button=e.currentTarget; const on=$('terminal').classList.toggle('wrap');button.setAttribute('aria-pressed', String(on));});
const done = status => ['completed','partial','failed','cancelled'].includes(status);
function badge(status) {const span=document.createElement('span');span.className=`badge ${Object.hasOwn(catalogs.en,status) ? status : 'neutral'}`;span.textContent=t(status);return span;}
function reason(result) {return t(Object.hasOwn(catalogs[locale], (result.explanation_key || 'reason_'+result.reason_code)) ? (result.explanation_key || 'reason_'+result.reason_code) : 'reason_fallback');}
function renderRows() {
  const body=$('result-rows');if(!body||!current) return;
  const fragment=document.createDocumentFragment();
  for(const result of current.results) {
    const row=document.createElement('tr'), name=document.createElement('td'), status=document.createElement('td'), detail=document.createElement('td');
    const bdi=document.createElement('bdi');bdi.dir='ltr';bdi.textContent=result.ascii || result.input;name.append(bdi);
    status.append(badge(result.status));detail.textContent=reason(result);
    if(result.suggestion) {const suggestion=document.createElement('bdi');suggestion.dir='ltr';suggestion.textContent=` → ${result.suggestion}`;detail.append(suggestion);}
    if(result.source) {const source=document.createElement('div');source.dir='ltr';source.textContent=result.source;source.className='small';detail.append(source);}
    row.append(name,status,detail);fragment.append(row);
  }
  body.replaceChildren(fragment);
}
function renderJob() {
  if(!current || !$('job-status')) return;
  const summary=current.summary;
  const counts=summary.statuses || {};
  $('stat-total').textContent=summary.total;
  $('stat-completed_count').textContent=summary.completed;
  $('stat-registered_count').textContent=counts.registered || 0;
  $('stat-attention').textContent=Object.entries(counts).filter(([k]) => !['registered','success'].includes(k)).reduce((n,[,v]) => n+v,0);
  const status=$('job-status');status.removeAttribute('data-i18n');status.className=`badge ${current.status}`;status.textContent=t(current.status);
  $('progress-label').textContent=`${summary.completed} / ${summary.total} · ${t(current.status)}`;
  $('job-progress').max=summary.total || 1;$('job-progress').value=summary.completed;
  $('empty-state').hidden=true;$('results-container').hidden=false;
  $('cancel-button').disabled=done(current.status);$('export-button').disabled=false;
  $('start-button').disabled=!done(current.status);$('start-button').classList.toggle('busy', !done(current.status));
  $('truncation').hidden=!current.truncated;
  renderRows();
}
function writeResult(result, streamed=false){if(result.output && !(streamed && current?.tool==='ping'))terminal.write(result.output);terminal.write(JSON.stringify({...result,output:undefined},null,2));}
function appendResult(result) {
  current.results.push(result);
  current.summary.completed=current.results.length;
  current.summary.statuses ||= {};
  current.summary.statuses[result.status]=(current.summary.statuses[result.status] || 0)+1;
  writeResult(result,true); renderJob();
}
function stopStream() {source?.close();source=null;clearTimeout(poll);}
async function refreshJob() {
  if(!current) return;
  current=await api(`/api/jobs/${current.job_id}`); renderJob();
  return current;
}
function connect() {
  if(!current || done(current.status)) return;
  source?.close();
  source=new EventSource(`/api/jobs/${current.job_id}/events?after=${lastEvent}`);
  for(const kind of ['state','progress','result','line','error','done','resync']) source.addEventListener(kind, event => {
    const id=Number(event.lastEventId); if(id && id<=lastEvent && kind!=='resync') return; lastEvent=id || lastEvent;
    const data=JSON.parse(event.data);
    if(kind==='result') appendResult(data);
    if(kind==='line') terminal.write(data.text);
    if(kind==='progress') {current.summary=data; renderJob();}
    if(kind==='state') {current.status=data.status;renderJob();}
    if(kind==='resync') {current=data;terminal.clear();for(const r of data.results) writeResult(r);renderJob();}
    if(kind==='done') {current.status=data.status;current.summary=data.summary;renderJob();stopStream();}
  });
  source.onerror=()=>{source?.close();source=null; if(current && !done(current.status)) {$('progress-label').textContent=t('reconnecting'); poll=setTimeout(async()=>{try {await refreshJob();for(const event of current.events.filter(e=>e.id>lastEvent)){if(event.type==='line')terminal.write(event.data.text);if(event.type==='result')writeResult(event.data,true);}lastEvent=Math.max(lastEvent,...current.events.map(e=>e.id));connect();}catch(error){toast(error.message);poll=setTimeout(connect,5000);}},2500);}};
}
$('tool-form')?.addEventListener('submit', async event => {
  event.preventDefault();const error=$('form-error');error.hidden=true;
  let data;
  if(page==='domain_batch') {
    const file=$('txt-file').files[0];
    if(file) {data=new FormData();data.set('text',$('domain-input').value);data.set('file',file);data.set('force_fresh',String($('force-fresh').checked));}
    else data={tool:page,text:$('domain-input').value,options:{force_fresh:$('force-fresh').checked}};
  } else {
    const tool=$('operation')?.value || page, options={};
    if(page==='dns') {options.record=$('record').value;options.resolver=$('custom-resolver').value.trim() || $('resolver').value;options.tcp=$('tcp').checked;}
    if(page==='ping') options.count=Number($('ping-count').value);
    data={tool, targets:[$('target-input').value.trim()], options};
  }
  $('start-button').disabled=true;$('start-button').classList.add('busy');
  try {stopStream();current=await api('/api/jobs',data);terminal.clear();lastEvent=Math.max(0,...current.events.map(e=>e.id));for(const result of current.results) writeResult(result);renderJob();connect();}
  catch(err) {error.textContent=err.message;error.hidden=false;$('start-button').disabled=false;$('start-button').classList.remove('busy');}
});
$('cancel-button')?.addEventListener('click',async()=>{try {await api(`/api/jobs/${current.job_id}/cancel`,{});await refreshJob();}catch(error){toast(error.message);}});
$('export-button')?.addEventListener('click',()=>{if(current) {const a=document.createElement('a');a.href=`/api/jobs/${current.job_id}/export?format=${$('export-format').value}&lang=${locale}`;a.download='';a.click();}});
$('txt-file')?.addEventListener('change',()=>{const file=$('txt-file').files[0];$('file-name').textContent=file ? `${file.name} · ${file.size} B` : t('file_help');if(file?.size>1048576){toast(t('input_too_large'));$('txt-file').value='';}});
function combinations() {
  const bases=$('base-names').value.split(/[,،\n]/).map(x=>x.trim()).filter(Boolean), suffixes=$('suffixes').value.split(/[,،\n]/).map(x=>x.trim().replace(/^\./,'')).filter(Boolean);
  if(!bases.length||!suffixes.length) throw new Error(t('empty_input'));
  if(bases.length*suffixes.length>1000) throw new Error(t('too_many_inputs'));
  return [...new Set(bases.flatMap(base=>suffixes.map(suffix=>`${base}.${suffix}`)))];
}
$('preview-generate')?.addEventListener('click',()=>{try {const list=combinations();$('generator-preview').textContent=`${list.length}\n${list.join('\n')}`;$('generator-preview').hidden=false;}catch(error){toast(error.message);}});
$('add-generate')?.addEventListener('click',()=>{try {$('domain-input').value=[$('domain-input').value,...combinations()].filter(Boolean).join('\n');}catch(error){toast(error.message);}});
$('operation')?.addEventListener('change',()=>{if(page==='http') $('target-input').placeholder=$('operation').value==='tls'?'example.com':'https://example.com';else if(page==='ip') $('target-input').placeholder=$('operation').value==='cidr'?'192.0.2.0/24':'1.1.1.1';});
function renderCapabilities() {
  const container=$('capabilities'); if(!container) return;
  container.replaceChildren();
  for(const [name,value] of [['server_origin',capabilities.platform],['ping',t(capabilities.ping?'available':'unavailable_cap')],['resources',Object.values(capabilities.resources).filter(r=>r.available).length+' / 5']]) {const el=document.createElement('div');el.className='capability';const label=document.createElement('strong');label.textContent=t(name);const valueEl=document.createElement('span');valueEl.className='badge neutral';valueEl.textContent=value;el.append(label,valueEl);container.append(el);}
}
function date(value) {if(!value) return '—';const date=new Date(value);return Number.isNaN(date.getTime())?value:date.toLocaleString(locale==='fa'?'fa-IR':'en-US');}
function renderResources() {
  const container=$('resources-list');if(!container||!resourceData)return;
  container.replaceChildren();
  for(const [key,info] of Object.entries(resourceData)) {
    const card=document.createElement('article');card.className='resource-card';
    const top=document.createElement('div');top.className='resource-top';const heading=document.createElement('h3');heading.dir='ltr';heading.textContent=key.toUpperCase();top.append(heading,badge(info.available ? info.status || 'bundled':'unsupported'));card.append(top);
    const url=document.createElement('a');url.href=info.source;url.rel='noreferrer';url.dir='ltr';url.textContent=info.source;card.append(url);
    for(const [label,value] of [['last_attempt',info.last_attempt],['last_success',info.last_success||info.retrieved_at],['publication',info.publication||info.last_modified]]) {const line=document.createElement('p');line.textContent=`${t(label)}: ${date(value)}`;card.append(line);}
    if(Date.now()-new Date(info.retrieved_at).getTime()>30*86400000) card.append(badge('stale'));
    if(info.error){const line=document.createElement('p');line.textContent=`${t('error')}: ${info.error}`;card.append(line);}
    const button=document.createElement('button');button.className='button secondary';button.textContent=t('update');button.addEventListener('click',async()=>{button.disabled=true;button.textContent=t('updating');try {await api('/api/resources/update',{resource:key});}catch(error){toast(error.message);}finally {await loadResources();}});card.append(button);container.append(card);
  }
}
async function loadResources(){try {resourceData=await api('/api/resources');renderResources();}catch(error){toast(error.message);}}
$('refresh-resources')?.addEventListener('click',loadResources);
$('password-form')?.addEventListener('submit',async e=>{e.preventDefault();const button=e.currentTarget.querySelector('button');button.disabled=true;try {await api('/auth/password',Object.fromEntries(new FormData(e.currentTarget)));toast(t('password_changed'));setTimeout(()=>location.assign('/auth/login'),1500);}catch(error){toast(error.message);button.disabled=false;}});
async function init() {
  translate();renderIcons();
  if(page==='login')return;
  try {capabilities=await api('/api/capabilities');renderCapabilities();$('private-warning').hidden=!capabilities.allow_private_targets;if(capabilities.mode==='public'){$('mode-label').removeAttribute('data-i18n');$('mode-label').dataset.i18n='public';$('mode-label').textContent=t('public');}if($('custom-resolver-label')) $('custom-resolver-label').hidden=capabilities.mode==='public';}catch(error){toast(error.message);}
  if(page==='resources')await loadResources();
}
init();

$('normalize-button')?.addEventListener('click', async()=>{try {const result=await api('/api/domain/normalize',{target:$('normalize-input').value});$('normalize-output').textContent=JSON.stringify(result,null,2);$('normalize-output').hidden=false;}catch(error){toast(error.message);}});
if($('suffix-list')) api('/api/suffixes').then(list=>{for(const suffix of list){const option=document.createElement('option');option.value=suffix.toLowerCase();option.textContent=option.value;$('suffix-list').append(option);}}).catch(error=>toast(error.message));
$('suffix-list')?.addEventListener('change',()=>{if($('suffix-list').value)$('suffixes').value=[$('suffixes').value,$('suffix-list').value].filter(Boolean).join(', ');});

const mobileMedia=matchMedia('(max-width:850px)');
if($('sidebar'))$('sidebar').inert=mobileMedia.matches;
mobileMedia.addEventListener('change',()=>{if($('sidebar')){if(!mobileMedia.matches)drawer(false);else $('sidebar').inert=!$('sidebar').classList.contains('open');}});
async function restoreCurrentJob(){
 if(page==='login'||!['overview','domain_batch','dns','ping','ip','http'].includes(page))return;
 try{const data=await api('/api/jobs'+(page==='overview'?'':'?tool='+page));if(!data.current||current)return;current=data.current;
 if(page==='overview'){const summary=current.summary,counts=summary.statuses||{};$('overview-job').hidden=false;$('stat-total').textContent=summary.total;$('stat-completed_count').textContent=summary.completed;$('stat-registered_count').textContent=counts.registered||0;$('stat-attention').textContent=Object.entries(counts).filter(([k])=>!['registered','success'].includes(k)).reduce((n,[,v])=>n+v,0);const group=['cidr','ptr','ip_rdap'].includes(current.tool)?'ip':current.tool==='tls'?'http':current.tool;$('overview-job-link').href='/tools/'+group;}
 else{lastEvent=Math.max(0,...current.events.map(e=>e.id));for(const result of current.results)writeResult(result);renderJob();connect();}
 }catch(error){toast(error.message);}
}
restoreCurrentJob();
