/* All published chapter content is loaded from ./data/chapters.json.
   Never include unpublished Notion content in this repo or in the JSON. */
const FINAL_SLUG = 'contact_error_hug_to_recharge';
const FINAL_TITLE = '接觸不良，請抱緊';
const els = {
  home: document.getElementById('home-view'), reader: document.getElementById('reader-view'),
  grid: document.getElementById('story-grid'), filters: document.getElementById('script-filters'),
  search: document.getElementById('story-search'), count: document.getElementById('story-count'),
  overlay: document.getElementById('age-overlay'), accept: document.getElementById('age-accept'),
  decline: document.getElementById('age-decline')
};
let chapters = [], activeFilter = '全部故事', pendingChapter = null;
document.getElementById('year').textContent = String(new Date().getFullYear());

function make(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = String(value);
  return node;
}
function isAdult(ch) { return /18\s*\+|成人|限制級/iu.test(ch.ageRating || ''); }
function storyUrl(ch) { return '#/read/' + encodeURIComponent(ch.slug); }
function finalPublished() { return chapters.some(c => c.slug === FINAL_SLUG); }
function listWithPlaceholder() {
  const items = [...chapters];
  if (!finalPublished()) items.push({ slug: FINAL_SLUG, title: FINAL_TITLE, originalScript: '即將登場', placeholder: true, chapterNumber: Infinity });
  return items;
}
function setRoute() {
  const hash = location.hash;
  const match = /^#\/read\/(.+)$/.exec(hash);
  if (match) {
    let slug;
    try { slug = decodeURIComponent(match[1]); } catch { slug = ''; }
    const chapter = listWithPlaceholder().find(c => c.slug === slug);
    if (!chapter) return showNotFound();
    if (isAdult(chapter) && sessionStorage.getItem('lc-age-confirmed') !== 'yes') return openAgeGate(chapter);
    return showReader(chapter);
  }
  els.reader.hidden = true; els.home.hidden = false;
  document.title = '戀愛 Casting：創造出屬於你的劇本';
  if (hash === '#stories' || hash === '#about') requestAnimationFrame(() => document.getElementById(hash.slice(1))?.scrollIntoView({behavior:'smooth'}));
  else window.scrollTo({top:0,behavior:'instant'});
}
function openAgeGate(chapter) { pendingChapter = chapter; els.overlay.hidden = false; document.body.classList.add('modal-open'); els.accept.focus(); }
function closeAgeGate() { els.overlay.hidden = true; document.body.classList.remove('modal-open'); pendingChapter = null; }
els.accept.addEventListener('click', () => { sessionStorage.setItem('lc-age-confirmed','yes'); const ch = pendingChapter; closeAgeGate(); if(ch) showReader(ch); });
els.decline.addEventListener('click', () => { closeAgeGate(); location.hash = '#stories'; setRoute(); });

function renderFilters() {
  const scripts = [...new Set(chapters.map(c=>c.originalScript).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-Hant'));
  const names = ['全部故事',...scripts]; els.filters.replaceChildren();
  for (const name of names) {
    const btn=make('button','filter-button'+(name===activeFilter?' active':''),name);
    btn.type='button'; btn.setAttribute('aria-pressed',String(name===activeFilter));
    btn.onclick=()=>{activeFilter=name;renderFilters();renderCards();};
    els.filters.append(btn);
  }
}
function renderCards() {
  const term=els.search.value.trim().toLocaleLowerCase();
  const filtered=listWithPlaceholder().filter(c => (activeFilter==='全部故事'||c.originalScript===activeFilter) && (`${c.title} ${c.originalScript||''}`).toLocaleLowerCase().includes(term));
  els.grid.replaceChildren();
  if (!filtered.length) els.grid.append(make('p','empty-state','目前沒有符合條件的故事，試試其他關鍵字。'));
  filtered.forEach((ch,i)=>{
    const card=make('a','story-card'+(ch.placeholder?' soon-card':''));card.href=storyUrl(ch);
    const top=make('div','card-top');
    const idLabel=ch.placeholder?'COMING SOON':Number.isFinite(Number(ch.chapterNumber))&&ch.chapterNumber!==null?`STORY ${String(ch.chapterNumber).padStart(2,'0')}`:`STORY ${String(i+1).padStart(2,'0')}`;
    top.append(make('span','card-id',idLabel));
    top.append(make('span','card-tag'+(ch.placeholder?' soon':isAdult(ch)?' age':''),ch.placeholder?'敬請期待':isAdult(ch)?'18+':'公開閱讀'));
    const title=make('h3',null,ch.title);
    const script=make('p','card-script',ch.placeholder?'最終篇 · 尚未公開':ch.originalScript?`原始劇本｜${ch.originalScript}`:'戀愛 Casting 衍生創作');
    const bottom=make('div','card-bottom');bottom.append(make('span',null,ch.placeholder?'A STORY YET TO COME':'READ THE STORY'),make('span',null,ch.placeholder?'♡':'↗'));
    card.append(top,title,script,bottom);els.grid.append(card);
  });
  els.count.textContent=`目前公開 ${chapters.length} 篇故事 · ${finalPublished()?'最終篇已公開':'另有 1 篇最終篇敬請期待'}`;
}
function safeHttpUrl(raw) { try { const u=new URL(raw,location.href); return ['https:','http:'].includes(u.protocol)?u.href:null; } catch { return null; } }
function addRuns(target,runs) {
  for(const run of (runs||[])) {
    let node=document.createTextNode(run.text||'');
    const flags=[['code','code'],['bold','strong'],['italic','em'],['underline','u'],['strikethrough','s']];
    for(const [key,tag] of flags) if(run[key]){const wrap=make(tag);wrap.append(node);node=wrap;}
    if(run.href&&safeHttpUrl(run.href)){const a=make('a');a.href=safeHttpUrl(run.href);a.target='_blank';a.rel='noopener noreferrer';a.append(node);node=a;}
    target.append(node);
  }
}
function addBlocks(parent,blocks) {
  let currentList=null,currentKind=null;
  for(const block of blocks||[]) {
    const type=block.type||'paragraph';
    if(type==='bulleted_list_item'||type==='numbered_list_item'){
      const kind=type==='bulleted_list_item'?'ul':'ol';
      if(!currentList||kind!==currentKind){currentList=make(kind);currentKind=kind;parent.append(currentList);}
      const item=make('li');addRuns(item,block.runs);currentList.append(item);if(block.children?.length)addBlocks(item,block.children);continue;
    }
    currentList=null;currentKind=null;
    let node;
    if(type==='divider') { parent.append(document.createElement('hr')); continue; }
    if(type==='image') {
      const src=safeHttpUrl(block.url);if(!src)continue;
      node=make('figure');const img=make('img');img.src=src;img.alt=(block.caption||'文章圖片').slice(0,150);img.loading='lazy';node.append(img);
      if(block.caption)node.append(make('figcaption',null,block.caption));parent.append(node);continue;
    }
    if(type==='to_do') {node=make('div','todo');const check=make('input');check.type='checkbox';check.disabled=true;check.checked=Boolean(block.checked);node.append(check);const span=make('span');addRuns(span,block.runs);node.append(span);parent.append(node);continue;}
    if(type==='table'){
      node=make('table');const body=make('tbody');for(const row of block.children||[]){const tr=make('tr');for(const cell of row.cells||[]){const td=make('td');addRuns(td,cell);tr.append(td);}body.append(tr);}node.append(body);parent.append(node);continue;
    }
    if(type==='toggle'){node=make('details');const summary=make('summary');addRuns(summary,block.runs);node.append(summary);addBlocks(node,block.children);parent.append(node);continue;}
    const tag=({'heading_1':'h2','heading_2':'h3','heading_3':'h4','quote':'blockquote','code':'pre','callout':'blockquote'})[type]||'p';
    node=make(tag);addRuns(node,block.runs);parent.append(node);
    if(block.children?.length)addBlocks(parent,block.children);
  }
}
function showReader(ch){
  closeAgeGate();els.home.hidden=true;els.reader.hidden=false;els.reader.replaceChildren();
  const wrap=make('article','reader-wrap');const back=make('a','back-link','← 返回故事目錄');back.href='#stories';
  wrap.append(back,make('p','reader-kicker',ch.placeholder?'FINAL EPISODE / COMING SOON':`LOVE CASTING / ${ch.originalScript||'STORY'}`),make('h1','reader-title',ch.title));
  wrap.append(make('p','reader-subline',ch.placeholder?'最終篇尚在創作中':`${ch.originalScript?'原始劇本：'+ch.originalScript+'　·　':''}${ch.ageRating||'一般'}${ch.chapterNumber?'　·　故事 '+ch.chapterNumber:''}`));
  const body=make('div','reader-body');
  if(ch.placeholder){const soon=make('div','coming-soon');soon.append(make('div','soon-icon','✳'),make('h2',null,'故事尚未落幕'),make('p',null,'《接觸不良，請抱緊》正在創作中。\n等下一次心跳，帶你走進最後一場劇本。'));body.append(soon);}
  else if(ch.blocks?.length){addBlocks(body,ch.blocks);}else{body.append(make('p',null,'這篇故事目前尚無可顯示的正文內容。'));}
  wrap.append(body,make('div','article-end','✳  THANK YOU FOR READING  ✳'));
  els.reader.append(wrap);document.title=ch.title+'｜戀愛 Casting';window.scrollTo({top:0,behavior:'instant'});
}
function showNotFound(){els.home.hidden=true;els.reader.hidden=false;els.reader.replaceChildren();const box=make('div','reader-wrap');box.append(make('h1','reader-title','找不到這篇故事'),make('p',null,'文章可能已下架，或網址不正確。'));const back=make('a','back-link','← 返回故事目錄');back.href='#stories';box.append(back);els.reader.append(box);}
async function load() {
  try{
    const response=await fetch('./data/chapters.json',{cache:'no-store'});
    if(!response.ok)throw new Error('無法取得資料');
    const data=await response.json();
    chapters=Array.isArray(data.chapters)?data.chapters.filter(c=>c&&typeof c.slug==='string'&&typeof c.title==='string'):[];
    chapters.sort((a,b)=>(Number(a.chapterNumber)||99999)-(Number(b.chapterNumber)||99999)||a.title.localeCompare(b.title,'zh-Hant'));
  }catch(err){console.warn('Story data loading issue:',err);chapters=[];}
  renderFilters();renderCards();setRoute();
}
els.search.addEventListener('input',renderCards);
window.addEventListener('hashchange',setRoute);
load();

// 首頁海浪：有影片才播放；尊重使用者「減少動態效果」設定。
(() => {
  const video = document.getElementById('hero-video');
  const hero = document.querySelector('.hero');
  if (!video || !hero) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const stop = () => { video.pause(); hero.classList.remove('video-playing'); };
  const start = () => {
    if (reducedMotion.matches) return stop();
    const playResult = video.play();
    if (playResult && typeof playResult.catch === 'function') playResult.catch(stop);
  };
  video.addEventListener('playing', () => { if (!reducedMotion.matches) hero.classList.add('video-playing'); });
  video.addEventListener('error', stop);
  video.addEventListener('stalled', stop);
  if (reducedMotion.addEventListener) reducedMotion.addEventListener('change', () => reducedMotion.matches ? stop() : start());
  if (document.visibilityState === 'visible') start();
  document.addEventListener('visibilitychange', () => document.visibilityState === 'hidden' ? stop() : start());
})();
