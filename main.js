'use strict';
const $ = (id) => document.getElementById(id);
const LABEL_TIME = new Intl.DateTimeFormat('vi-VN', {timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
const STORE_KEY = 'salehunter-favorites-v2';
let remote = {items: [], sources: [], stats: {}, is_scanning: false, last_updated: null, has_source_errors: false};
let remoteVersion = '';
const settings = window.SALEHUNTER_CONFIG || {};
const feedUrl = String(settings.dataUrl || './data/offers.json').trim();
const reloadMs = Math.max(30, Math.min(3600, Number(settings.reloadSeconds) || 60)) * 1000;
let currentTab = 'all';
let visibleCount = 36;
let favorites = new Set();
function expired(item) {
  if (!item.expires_at) return false;
  const time = Date.parse(item.expires_at);
  return Number.isFinite(time) && time <= Date.now();
}

let toastTimer, fetchBusy = false, queryTimer, timer;
try { favorites = new Set(JSON.parse(localStorage.getItem(STORE_KEY) || '[]')); } catch { /* storage disabled */ }

function el(tag, cls, txt) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (txt !== undefined) node.textContent = String(txt);
  return node;
}
function toast(message) {
  const node = $('toast'); node.textContent = message; node.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => node.classList.remove('show'), 3300);
}
function shortTime(value) {
  if (!value) return 'Chưa có lần quét thành công';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Chưa rõ' : LABEL_TIME.format(date);
}
function safeLink(raw) {
  try { const u = new URL(raw); return u.protocol === 'https:' && !u.username && !u.password ? u.href : null; }
  catch { return null; }
}
function setTab(value) {
  currentTab = value;
  visibleCount = 36;
  document.querySelectorAll('[data-tab]').forEach(x => x.classList.toggle('active', x.dataset.tab === value));
  document.querySelectorAll('[data-nav]').forEach(x => x.classList.toggle('active', x.dataset.nav === value));
  renderCards();
}
function filtered() {
  const q = $('search').value.trim().toLocaleLowerCase('vi-VN');
  const kind = $('categoryFilter').value;
  const state = $('statusFilter').value;
  const rows = (remote.items || []).filter(item => {
    if (expired(item)) return false;
    if (currentTab === 'shopee' && item.platform !== 'Shopee') return false;
    if (currentTab === 'tiktok' && item.platform !== 'TikTok Shop') return false;
    if (currentTab === 'copy' && !item.code) return false;
    if (currentTab === 'saved' && !favorites.has(item.id)) return false;
    if (kind !== 'all' && kind !== item.kind) return false;
    if (state === 'fresh' && item.stale) return false;
    if (state === 'stale' && !item.stale) return false;
    return !q || [item.title, item.description, item.source, item.platform, item.code, item.min_spend]
      .filter(Boolean).join(' ').toLocaleLowerCase('vi-VN').includes(q);
  });
  const stamp = item => new Date(item.published_at || item.last_seen || 0).getTime() || 0;
  const sorting = $('sortFilter').value;
  if (sorting === 'code') rows.sort((a,b) => Number(!!b.code)-Number(!!a.code) || Number(a.stale)-Number(b.stale) || stamp(b)-stamp(a));
  else if (sorting === 'platform') rows.sort((a,b) => a.platform.localeCompare(b.platform) || stamp(b)-stamp(a));
  else rows.sort((a,b) => Number(a.stale)-Number(b.stale) || stamp(b)-stamp(a));
  return rows;
}
function makeCard(item) {
  const card = el('article', 'deal-card' + (item.stale ? ' deal-stale' : ''));
  const top = el('div','card-top');
  const platform = el('div','platform');
  platform.append(el('span','platform-logo'+(item.platform==='TikTok Shop'?' tiktok':''),item.platform==='TikTok Shop'?'♪':'S'),
                  el('span',null,item.platform));
  top.append(platform,el('span','kind-badge'+(item.kind==='Freeship'?' freeship':item.kind==='Flash sale'?' flash':''),item.kind));
  card.append(top);
  if (item.stale) card.append(el('div','freshness-warning','⚠ Nguồn đang lỗi • Dữ liệu lưu từ lần quét trước'));
  card.append(el('h3','card-title',item.title));
  card.append(el('div','discount'+(!item.discount?' empty-discount':''),item.discount ? 'Giảm '+item.discount : 'Ưu đãi • Xem điều kiện'));
  if (item.description) card.append(el('div','description',item.description));
  if (item.min_spend) card.append(el('div','condition-note','Đơn tối thiểu: '+item.min_spend));
  if (item.expires_at) card.append(el('div','condition-note','Hạn công bố: '+shortTime(item.expires_at)));
  const codeWrap=el('div','code-wrap');
  if (item.code) {
    const content=el('div'); content.append(el('span','code-label','MÃ ĐƯỢC CÔNG BỐ'),el('strong','code-value',item.code));
    const copy=el('button','copy-small','▢ Sao chép'); copy.type='button';
    copy.setAttribute('aria-label','Sao chép mã '+item.code);
    copy.addEventListener('click',()=>copyCode(item.code)); codeWrap.append(content,copy);
  } else {
    const content=el('div'); content.append(el('span','code-label','CHƯA CÓ MÃ NHẬP TAY'),
      el('span','code-none','Mở nguồn để xem cách nhận ưu đãi'));
    codeWrap.append(content,el('span','copy-icon','↗'));
  }
  card.append(codeWrap);
  card.append(el('div','verify-note','Chưa xác minh mã còn lượt / áp dụng được ở thanh toán'));
  const foot=el('div','card-foot');
  const source=el('span','source-link','Nguồn: '+(item.source||'Chưa rõ'));
  source.title=item.source||'';
  foot.append(source,el('span',null,shortTime(item.published_at || item.last_seen)));
  card.append(foot);
  const actions=el('div','bottom-actions');
  const href=safeLink(item.url);
  const link=el('a','view-btn',item.direct_link?'↗ Mở trên sàn':'↗ Xem thông tin nguồn');
  if (href) {link.href=href; link.target='_blank';link.rel='noopener noreferrer';}
  else {link.setAttribute('aria-disabled','true');}
  const active=favorites.has(item.id);
  const save=el('button','save-btn'+(active?' saved':''),active?'♥':'♡'); save.type='button';
  save.setAttribute('aria-label',active?'Bỏ lưu':'Lưu ưu đãi');
  save.addEventListener('click',()=>{
    favorites.has(item.id) ? favorites.delete(item.id) : favorites.add(item.id);
    try {localStorage.setItem(STORE_KEY,JSON.stringify([...favorites]));} catch { /* blocked */ }
    renderCards(); $('savedCount').textContent=favorites.size;
    toast(favorites.has(item.id)?'Đã lưu vào danh sách yêu thích':'Đã bỏ lưu');
  });
  actions.append(link,save); card.append(actions);
  return card;
}
async function copyCode(code) {
  try {
    if (!/^[A-Z0-9][A-Z0-9_-]{4,27}$/i.test(code)) throw new Error('Mã không đúng định dạng');
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(code);
    else {
      const field=el('textarea'); field.value=code;field.style.position='fixed';field.style.opacity='0';
      document.body.append(field);field.focus();field.select();
      const success=document.execCommand('copy');field.remove();if(!success) throw Error('Clipboard bị khóa');
    }
    toast('Đã sao chép: '+code+' • Hãy kiểm tra mã tại thanh toán');
  } catch {toast('Không thể sao chép tự động. Hãy chọn mã hiển thị và sao chép thủ công.');}
}
function renderSources() {
  const panel=$('sourceDetails');panel.replaceChildren();
  const wrap=el('div','source-list');
  if (!remote.sources.length) wrap.append(el('p',null,'Chưa cấu hình nguồn dữ liệu.'));
  for (const source of remote.sources) {
    const row=el('div','source-row');const left=el('div');
    left.append(el('strong',null,source.name),el('small',null,'Quét gần nhất: '+shortTime(source.last_attempt)));
    if (source.error) left.append(el('small','source-error',source.error));
    const caption=source.ok===null?'Chưa quét':source.ok?`${source.count} mục • thành công`:'Nguồn lỗi • dùng cache nếu có';
    row.append(left,el('span',source.ok===null?'pending':source.ok?'ok':'fail',caption));wrap.append(row);
  }
  panel.append(wrap);
}
function renderCards() {
  const rows=filtered();$('resultsCount').textContent=rows.length+' ưu đãi';
  const fragment=document.createDocumentFragment();
  for (const item of rows.slice(0,visibleCount)) fragment.append(makeCard(item));
  $('dealCards').replaceChildren(fragment);
  $('showMore').hidden=rows.length<=visibleCount;
  const empty=rows.length===0;
  $('emptyState').hidden=!empty;
  $('emptyText').textContent=remote.is_scanning?'Đang quét; dữ liệu sẽ xuất hiện nếu nguồn có ưu đãi phù hợp.' :
    remote.items.length?'Không có kết quả với bộ lọc đang chọn. Hãy thay đổi từ khóa hoặc sàn.':'Chưa có ưu đãi được nguồn xác nhận đã công bố gần đây. Bạn có thể mở kho mã trực tiếp trên các sàn.';
}
function render() {
  const active=(remote.items||[]).filter(item => !expired(item));
  const metrics={...remote.stats,all:active.length, shopee:active.filter(x=>x.platform==='Shopee').length,
    tiktok:active.filter(x=>x.platform==='TikTok Shop').length, codes:active.filter(x=>!!x.code).length};
  $('metricAll').textContent=metrics.all??remote.items.length;
  $('metricShopee').textContent=metrics.shopee??0;
  $('metricTikTok').textContent=metrics.tiktok??0;
  $('metricCodes').textContent=metrics.codes??0;
  $('navCount').textContent=metrics.all??0;
  $('savedCount').textContent=favorites.size;
  $('lastUpdated').textContent='Quét thành công: '+shortTime(remote.last_updated);
  for (const id of ['topRefresh','sidebarRefresh','emptyRefresh']) $(id).disabled=false;
  $('topRefresh').querySelector('.refresh-icon').classList.toggle('spin',!!remote.is_scanning);
  const notices=$('noticeArea'); notices.replaceChildren();
  if (!settings.dataUrl) notices.append(el('div','notice','Chưa kết nối nguồn JSON GitHub. Hiện chỉ đọc dữ liệu đi kèm lúc tải mã nguồn lên Space. Xem README để bật tự động cập nhật.'));
  if (remote.is_scanning) notices.append(el('div','notice','Dữ liệu nguồn đang cập nhật.'));
  if (remote.has_source_errors) notices.append(el('div','notice error','Một số nguồn không truy cập được. Các ưu đãi từ cache được đánh dấu cảnh báo; hãy kiểm tra tại nguồn.'));
  if (metrics.stale) notices.append(el('div','notice','Có '+metrics.stale+' ưu đãi lấy từ dữ liệu lưu khi nguồn lỗi. Không xem đây là voucher đã được xác minh.'));
  if (remote.last_attempt && Date.now() - Date.parse(remote.last_attempt) > 90 * 60 * 1000) {
    notices.append(el('div','notice error','Dữ liệu đã quá 90 phút chưa được quét lại. Kiểm tra GitHub Actions hoặc các nguồn trước khi sử dụng mã.'));
  }
  renderCards();renderSources();
}
async function load({force = false} = {}) {
  if (fetchBusy) return;
  fetchBusy = true;
  try {
    // Data is produced by scheduled GitHub Actions, not a HF backend endpoint.
    const address = new URL(feedUrl, window.location.href);
    if (!['https:', 'http:'].includes(address.protocol)) throw Error('Nguồn dữ liệu không hợp lệ');
    // Polling uses conditional browser revalidation. Force-refresh bypasses stale caches.
    if (force) address.searchParams.set('_refresh', String(Date.now()));
    const response = await fetch(address.toString(), {cache: force ? 'no-store' : 'no-cache', mode:'cors'});
    if (!response.ok) throw new Error('HTTP '+response.status);
    const data = await response.json();
    if (!data || !Array.isArray(data.items) || !Array.isArray(data.sources))
      throw Error('JSON thiếu danh sách ưu đãi hoặc trạng thái nguồn');
    const checksum = JSON.stringify([data.last_attempt, data.stats, data.sources, data.items]);
    if (checksum !== remoteVersion || force) {
      remoteVersion = checksum;
      remote = data;
      render();
    }
    if (force) toast('Đã tải dữ liệu công khai mới nhất đang có');
  } catch(error) {
    $('noticeArea').replaceChildren(el('div','notice error',
      'Không tải được nguồn dữ liệu: '+error.message+' • Danh sách đã xem vẫn được giữ trên trang. Kiểm tra cấu hình JSON và repo GitHub public.'));
    if (force) toast('Không thể cập nhật. Hãy kiểm tra nguồn dữ liệu.');
  } finally {fetchBusy = false;}
}
function refresh() { return load({force:true}); }
function clearFilters() {
  $('search').value='';$('categoryFilter').value='all';$('statusFilter').value='all';$('sortFilter').value='newest';setTab('all');
}
function schedule() {
  clearTimeout(timer);
  timer=setTimeout(async()=>{if (!document.hidden) await load();schedule();},reloadMs);
}
for (const element of document.querySelectorAll('[data-tab]')) element.addEventListener('click',()=>setTab(element.dataset.tab));
for (const element of document.querySelectorAll('[data-nav]')) element.addEventListener('click',()=>{setTab(element.dataset.nav);$('deals').scrollIntoView({behavior:'smooth'});});
for (const id of ['topRefresh','sidebarRefresh','emptyRefresh']) $(id).addEventListener('click',refresh);
$('search').addEventListener('input',()=>{clearTimeout(queryTimer);queryTimer=setTimeout(()=>{visibleCount=36;renderCards();},180);});
for (const id of ['categoryFilter','sortFilter','statusFilter']) $(id).addEventListener('change',()=>{visibleCount=36;renderCards();});
$('showMore').addEventListener('click',()=>{visibleCount+=36;renderCards();});
$('clearFilters').addEventListener('click',clearFilters);
$('jumpToDeals').addEventListener('click',()=>$('deals').scrollIntoView({behavior:'smooth'}));
$('toggleSources').addEventListener('click',()=>{
  const expanded=$('sourceDetails').hidden; $('sourceDetails').hidden=!expanded;
  $('toggleSources').setAttribute('aria-expanded',String(expanded));
  $('toggleSources').textContent=expanded?'Thu gọn ⌃':'Xem chi tiết ⌄';
});
document.addEventListener('keydown',event=>{
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k') {event.preventDefault();$('search').focus();}
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden) load();});
load().finally(schedule);
