'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const config = window.SALEHUNTER_CONFIG || {};
  const feedUrl = typeof config.dataUrl === 'string' && config.dataUrl.trim() ? config.dataUrl.trim() : './data/offers.json';
  const reloadMs = Math.max(60, Math.min(Number(config.reloadSeconds) || 180, 3600)) * 1000;
  const STORE_FAV = 'salehunter-v3-favs';
  const STORE_THEME = 'salehunter-v3-theme';
  const STORE_BAD = 'salehunter-v3-reported-codes';
  const state = {feed: {items:[],sources:[],last_updated:null,stats:{}},platform:'all',mode:'codes',query:'',sort:'featured',visible:24,loading:false,hasLoaded:false,bundledFallback:false};
  const favorites = new Set(safeRead(STORE_FAV, []));
  const reportedCodes = new Set(safeRead(STORE_BAD, []).map(s => String(s).toUpperCase()));
  const excludedCodes = new Set(['SVIPDDVKH0110MOC200A', 'SVIPDDVKH0110M0C200A']); // Reported in the uploaded Shopee screenshot.
  let toastTimer;
  let refreshTimer;
  let searchTimer;
  let lastSignature = '';
  const icon = (name) => { const svg = document.createElementNS('http://www.w3.org/2000/svg','svg'); svg.setAttribute('class','icon'); svg.setAttribute('aria-hidden','true'); const use=document.createElementNS('http://www.w3.org/2000/svg','use');use.setAttribute('href','#i-'+name);svg.append(use);return svg; };
  const el = (tag,cls,txt) => {const node = document.createElement(tag); if(cls) node.className=cls; if(txt!==undefined && txt!==null) node.textContent=String(txt);return node;};
  function safeRead(key, fallback){try{const obj=JSON.parse(localStorage.getItem(key));return Array.isArray(obj)?obj:fallback}catch{return fallback}}
  function dateValue(raw){const n=Date.parse(raw || '');return Number.isFinite(n)?n:null}
  function formatted(raw){const time=dateValue(raw);if(time===null)return 'Chưa rõ';return new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(time));}
  function expiration(raw){const time=dateValue(raw);if(time===null)return 'Chưa công bố';return new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date(time));}
  function validLink(raw){try{const url=new URL(String(raw||''));return url.protocol==='https:'&&!url.username&&!url.password?url.href:null}catch{return null}}
  function hasCode(item){return typeof item.code==='string' && /^[A-Z0-9][A-Z0-9_-]{4,27}$/i.test(item.code)}
  function codeKey(item){return String(item.code||'').trim().toUpperCase()}
  function hiddenBadCode(item){return hasCode(item) && (reportedCodes.has(codeKey(item)) || excludedCodes.has(codeKey(item)))}
  async function loadExclusions(){
    try {const url=new URL(config.excludedCodesUrl||'./data/excluded_codes.json',document.baseURI);
      if(!['http:','https:'].includes(url.protocol))return;
      const res=await fetch(url.href,{cache:'no-cache'});if(!res.ok)return;
      const payload=await res.json(); if(!Array.isArray(payload.codes))return;
      for(const value of payload.codes){if(typeof value==='string'&&/^[A-Z0-9][A-Z0-9_-]{4,27}$/i.test(value))excludedCodes.add(value.toUpperCase())}
    }catch{
      // Keep the explicitly reported code and the packaged fallback denylist.
    }
  }
  function reportCode(item){
    if(!hasCode(item))return;
    reportedCodes.add(codeKey(item));
    try{localStorage.setItem(STORE_BAD,JSON.stringify([...reportedCodes].slice(-500)))}catch{}
    render();
    showToast('Đã ẩn mã trên thiết bị này. Chưa gửi báo cáo về máy chủ.');
  }
  function activeItems(){return (state.feed.items||[]).filter(item=>item&&typeof item==='object'&&(item.platform==='Shopee'||item.platform==='TikTok Shop')&&(!dateValue(item.expires_at)||dateValue(item.expires_at)>Date.now())&&!hiddenBadCode(item));}
  function showToast(msg){const node=$('toast');node.textContent=msg;node.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.classList.remove('show'),3500)}
  async function copyText(value){
    try{
      if(!/^[A-Z0-9][A-Z0-9_-]{4,27}$/i.test(value))throw Error('Mã không đúng định dạng');
      if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(value);
      else {const field=el('textarea');field.value=value;field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.focus();field.select();if(!document.execCommand('copy'))throw Error('Clipboard');field.remove();}
      showToast('✓ Đã sao chép mã '+value+' · Kiểm tra khi thanh toán');
    }catch{showToast('Không thể copy tự động. Bạn có thể chọn ký tự mã để sao chép thủ công.');}
  }
  function sortList(items){const result=[...items];const time=(x)=>dateValue(x.published_at)||dateValue(x.last_seen)||0;
    result.sort((a,b)=>{switch(state.sort){
      case 'recent':return time(b)-time(a);
      case 'expiry':return (dateValue(a.expires_at)||Number.MAX_SAFE_INTEGER)-(dateValue(b.expires_at)||Number.MAX_SAFE_INTEGER);
      case 'platform':return a.platform.localeCompare(b.platform,'vi')||time(b)-time(a);
      default:return Number(hasCode(b))-Number(hasCode(a))||Number(!b.stale)-Number(!a.stale)||time(b)-time(a);
    }});return result;
  }
  function filtered(){const q=state.query.toLocaleLowerCase('vi').trim();return sortList(activeItems().filter(item=>
    (state.platform==='all'||item.platform===state.platform)&&
    (state.mode==='all'||state.mode==='codes'&&hasCode(item)||state.mode==='claim'&&!hasCode(item)||state.mode==='saved'&&favorites.has(item.id))&&
    (!q||[item.title,item.description,item.code,item.discount,item.min_spend,item.source].join(' ').toLocaleLowerCase('vi').includes(q))));}
  function renderMetrics(){const items=activeItems(), codes=items.filter(hasCode).length, shopee=items.filter(x=>x.platform==='Shopee').length, tiktok=items.filter(x=>x.platform==='TikTok Shop').length;
    for(const [id,value] of Object.entries({statAll:items.length,statCodes:codes,statShopee:shopee,statTikTok:tiktok,navTotal:items.length,navCodes:codes,navSaved:favorites.size,countAll:items.length,countShopee:shopee,countTikTok:tiktok}))$(id).textContent=String(value);
    $('updated').replaceChildren(icon('clock'),document.createTextNode('Cập nhật nguồn: '+formatted(state.feed.last_updated)));
  }
  function card(item){
    const isTik=item.platform==='TikTok Shop';const card=el('article','offer-card'+(isTik?' tiktok':''));
    const cover=el('div','offer-cover');cover.append(el('div','cover-orb'),el('div','cover-circle'));
    const top=el('div','cover-top'),merchant=el('span','merchant-pill');merchant.append(el('span','merchant-pill-icon',isTik?'♪':'S'),document.createTextNode(item.platform));
    top.append(merchant,el('span','type-badge',hasCode(item)?'CÓ MÃ COPY':'NHẬN VOUCHER'));
    let visual=item.discount?String(item.discount):'';if(!visual)visual=hasCode(item)?'MÃ GIẢM GIÁ':'ƯU ĐÃI';
    cover.append(top,el('div','cover-discount',visual.length>30?visual.slice(0,28)+'…':visual),el('div','cover-subtitle',hasCode(item)?'SAO CHÉP MÃ NHẬP TAY':'XEM HƯỚNG DẪN NHẬN MÃ'));
    card.append(cover);
    if(item.stale)card.append(el('div','stale-banner','⚠ Nguồn đang lỗi · Dữ liệu từ lần quét trước'));
    const body=el('div','offer-body');body.append(el('h3','offer-title',item.title||'Ưu đãi chưa có tên'));
    const conditions=el('div','offer-conditions');conditions.append(el('span',null,item.min_spend?String(item.min_spend):'Điều kiện: xem nguồn'),el('span',null,item.expires_at?'HSD '+expiration(item.expires_at):'Hạn: chưa công bố'));body.append(conditions);
    const coupon=el('div','coupon-box'+(hasCode(item)?'':' no-code')),content=el('div');content.append(el('span','code-label',hasCode(item)?'MÃ ĐƯỢC CÔNG BỐ':'KHÔNG CÓ CHUỖI MÃ NHẬP TAY'),el('strong','code-value',hasCode(item)?item.code:'Nhận ưu đãi trên trang nguồn'));coupon.append(content);
    if(hasCode(item)){const b=el('button','copy-btn');b.type='button';b.append(icon('copy'),document.createTextNode('Copy mã'));b.setAttribute('aria-label','Sao chép mã '+item.code);b.addEventListener('click',()=>copyText(item.code));coupon.append(b);}
    else coupon.append(icon('external'));
    body.append(coupon,el('div','card-disclaimer','⚠ CHƯA XÁC MINH tại thanh toán. Mã có thể hết lượt, giới hạn tài khoản hoặc không áp dụng cho đơn hàng.'));
    if(hasCode(item)){const report=el('button','report-code-btn','⚑ Báo mã không dùng được · Ẩn trên thiết bị');report.type='button';report.addEventListener('click',()=>reportCode(item));body.append(report);}
    const footer=el('div','card-footer');const source=el('span','card-source');source.append(document.createTextNode('Nguồn: '),el('strong',null,item.source||'Công khai'));source.title=item.source||'';footer.append(source);
    const actions=el('div','card-actions');const href=validLink(item.url);const out=el('a','open-source');out.append(document.createTextNode('Xem nguồn'),icon('external'));
    if(href){out.href=href;out.target='_blank';out.rel='noopener noreferrer';}else {out.removeAttribute('href');out.setAttribute('aria-disabled','true');}
    actions.append(out);const fav=el('button','save-btn'+(favorites.has(item.id)?' saved':''));fav.type='button';fav.append(icon('heart'));fav.setAttribute('aria-label',favorites.has(item.id)?'Bỏ lưu ưu đãi':'Lưu ưu đãi');fav.addEventListener('click',()=>{
      if(favorites.has(item.id))favorites.delete(item.id);else favorites.add(item.id);
      try{localStorage.setItem(STORE_FAV,JSON.stringify([...favorites].slice(-500)))}catch{}
      renderMetrics();renderCards();showToast(favorites.has(item.id)?'♡ Đã thêm vào mục Đã lưu':'Đã bỏ lưu ưu đãi');
    });actions.append(fav);footer.append(actions);body.append(footer);card.append(body);return card;
  }
  function renderCards(){const rows=filtered();$('resultText').textContent=rows.length+' ưu đãi phù hợp';const grid=$('cards');const fragment=document.createDocumentFragment();
    for(const item of rows.slice(0,state.visible))fragment.append(card(item));grid.replaceChildren(fragment);
    $('showMore').hidden=rows.length<=state.visible;
    const empty=rows.length===0; $('empty').hidden=!empty;
    if(empty){let title='Chưa tìm thấy mã phù hợp',desc='Hãy thử thay đổi bộ lọc hoặc tìm kiếm.';
      if(state.mode==='codes'&&!state.query&&state.platform==='all'){title='Chưa tìm được mã nhập tay mới';desc='Bộ quét chưa trích xuất được chuỗi mã hợp lệ từ các nguồn hiện tại. Bạn có thể chọn “Tất cả” để xem các ưu đãi khác hoặc kiểm tra trạng thái nguồn bên dưới.'}
      if(state.mode==='saved'){title='Chưa có ưu đãi đã lưu';desc='Nhấn nút trái tim ở thẻ ưu đãi để lưu lại và tìm nhanh lần sau.'}
      if(!state.hasLoaded){title='Đang tải dữ liệu';desc='Đang kết nối với kho voucher công khai trên GitHub…'}
      $('emptyTitle').textContent=title;$('emptyDesc').textContent=desc;
    }
  }
  function renderSources(){const area=$('sources');const fragment=document.createDocumentFragment();const rows=Array.isArray(state.feed.sources)?state.feed.sources:[];
    if(!rows.length)fragment.append(el('p',null,'Chưa có dữ liệu trạng thái nguồn.'));
    for(const s of rows){const row=el('div','source-row'),left=el('div');left.append(el('strong',null,s.name||s.key||'Nguồn'),el('small',null,'Quét thành công: '+formatted(s.last_success)));const badge=el('span','source-status'+(s.ok===false?' failed':s.ok===null?' pending':''),s.ok===false?'Lỗi / cache':s.ok===true?`${Number(s.count)||0} mục`:'Chưa chạy');row.append(left,badge);fragment.append(row)}area.replaceChildren(fragment);
  }
  function notice(message,error=false){const box=el('div','alert'+(error?' error':''));box.append(icon('info'),el('span',null,message));return box;}
  function renderAlerts(){const area=$('alerts');area.replaceChildren();const feed=state.feed;const items=activeItems();if(feed.has_source_errors)area.append(notice('Một hoặc nhiều nguồn đang lỗi. Danh sách có thể chứa dữ liệu lưu từ lần quét thành công trước đó; hãy xác minh tại nguồn.',true));
    const age=dateValue(feed.last_attempt);if(age&&Date.now()-age>1000*60*100)area.append(notice('Dữ liệu đã lâu chưa được quét. Hãy kiểm tra GitHub Actions nếu cần thông tin mới nhất.',true));
    if(state.hasLoaded&&!items.length)area.append(notice('Hiện chưa có ưu đãi phù hợp được công bố từ các nguồn đã cấu hình. Không có mã giả được thêm vào.'));
    if(reportedCodes.size)area.append(notice('Bạn đã ẩn '+reportedCodes.size+' mã lỗi trên thiết bị này. Báo cáo chưa được gửi tới quản trị viên.'));
    area.append(notice('Lưu ý: Mã công bố trên website thứ ba KHÔNG đồng nghĩa Shopee/TikTok Shop chấp nhận mã. Chỉ sàn mới xác nhận khi áp dụng đơn hàng.'));
    if(!config.dataUrl)area.append(notice('Chưa kết nối URL JSON bên ngoài. Hiện chỉ hiển thị dữ liệu đi kèm trong Space.'));
  }
  function render(){renderMetrics();renderAlerts();renderCards();renderSources()}
  function setMode(mode){if(!['codes','all','claim','saved'].includes(mode))return;state.mode=mode;state.visible=24;document.querySelectorAll('[data-mode]').forEach(b=>{b.classList.toggle('active',b.dataset.mode===mode);b.setAttribute('aria-pressed',String(b.dataset.mode===mode))});document.querySelectorAll('[data-side]').forEach(b=>b.classList.toggle('active',b.dataset.side===mode));renderCards()}
  function setPlatform(name){state.platform=name;state.visible=24;document.querySelectorAll('[data-platform]').forEach(b=>{b.classList.toggle('active',b.dataset.platform===name);b.setAttribute('aria-pressed',String(b.dataset.platform===name))});document.querySelectorAll('[data-merchant]').forEach(b=>b.classList.toggle('active',b.dataset.merchant===name));renderCards()}
  async function load(force=false){if(state.loading)return;state.loading=true;$('refreshBtn').disabled=true;
    try {const address=new URL(feedUrl,document.baseURI);if(!['http:','https:'].includes(address.protocol))throw Error('URL không hợp lệ');if(force)address.searchParams.set('_v',Date.now());
      const res=await fetch(address.href,{mode:'cors',cache:force?'no-store':'no-cache'});if(!res.ok)throw Error('HTTP '+res.status);let data=await res.json();if(!data||!Array.isArray(data.items)||!Array.isArray(data.sources))throw Error('Dữ liệu JSON sai cấu trúc');
      state.bundledFallback=false;
      // Never inject hardcoded codes when GitHub has an empty successful result.
      const sign=JSON.stringify([data.last_attempt,data.items,data.sources,state.bundledFallback]);state.hasLoaded=true;
      if(sign!==lastSignature||force){lastSignature=sign;state.feed=data;render()}
      if(force)showToast('Đã tải dữ liệu nguồn. Mã chưa được xác minh tại thanh toán.');
    }catch(err){
      state.hasLoaded=true;
      let recovered=false;
      if(!state.feed.items.length){
        try{
          const address= new URL(config.fallbackDataUrl||'./data/offers.json',document.baseURI);
          const fallback=await fetch(address.href,{cache:'no-cache'});
          if(fallback.ok){
            const local=await fallback.json();
            if(Array.isArray(local.items) && Array.isArray(local.sources)){
              state.feed=local;state.bundledFallback=false;recovered=true;
            }
          }
        }catch{}
      }
      render();
      $('alerts').prepend(notice('Không tải được dữ liệu GitHub ('+err.message+'). '+
        (recovered?'Đang hiển thị danh sách cục bộ (không có mã cũ được thêm vào).':'Kiểm tra GitHub Actions hoặc đường dẫn data/offers.json.'),true));
      if(force)showToast(recovered?'Chưa có dữ liệu mới; không thêm mã cũ':'Không thể tải dữ liệu; kiểm tra tệp nguồn.');
    }
    finally{state.loading=false;$('refreshBtn').disabled=false;}
  }
  function setupTheme(){let theme;try{theme=localStorage.getItem(STORE_THEME)}catch{}if(theme==='dark')document.body.classList.add('dark');$('themeToggle').addEventListener('click',()=>{const yes=document.body.classList.toggle('dark');try{localStorage.setItem(STORE_THEME,yes?'dark':'light')}catch{}showToast(yes?'Đã bật giao diện tối':'Đã bật giao diện sáng')})}
  function setup(){setupTheme();document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
    document.querySelectorAll('[data-platform]').forEach(b=>b.addEventListener('click',()=>setPlatform(b.dataset.platform)));
    document.querySelectorAll('[data-side]').forEach(b=>b.addEventListener('click',()=>{setMode(b.dataset.side);$('deals').scrollIntoView({behavior:'smooth'})}));
    document.querySelectorAll('[data-merchant]').forEach(b=>b.addEventListener('click',()=>{setPlatform(b.dataset.merchant);$('deals').scrollIntoView({behavior:'smooth'})}));
    $('search').addEventListener('input',e=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.query=e.target.value;state.visible=24;renderCards()},130)});
    $('sort').addEventListener('change',e=>{state.sort=e.target.value;renderCards()});
    $('refreshBtn').addEventListener('click',()=>load(true));$('emptyRefresh').addEventListener('click',()=>load(true));$('viewAll').addEventListener('click',()=>{state.query='';$('search').value='';setMode('all')});
    $('showMore').addEventListener('click',()=>{state.visible+=24;renderCards()});
    $('heroJump').addEventListener('click',()=>{setMode('codes');$('deals').scrollIntoView({behavior:'smooth'})});
    $('sourcesToggle').addEventListener('click',()=>{const expanded=$('sourcesToggle').getAttribute('aria-expanded')==='true';$('sourcesToggle').setAttribute('aria-expanded',String(!expanded));$('sources').hidden=expanded});
    document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('search').focus()}});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)load(false)});
    refreshTimer=setInterval(()=>{if(!document.hidden)load(false)},reloadMs);
    setPlatform('all');setMode('codes');loadExclusions().then(()=>{render();load()});
  }
  setup();
})();
