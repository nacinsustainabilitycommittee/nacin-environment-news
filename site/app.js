'use strict';
const list=document.querySelector('#articles');
const count=document.querySelector('#count');
const search=document.querySelector('#search');
const sort=document.querySelector('#sort');
let articles=[];
function node(tag,cls,value){const n=document.createElement(tag);if(cls)n.className=cls;if(value)n.textContent=value;return n;}
function render(){const q=search.value.toLowerCase().trim();const matched=articles.filter(x=>[x.title,x.source,x.source_country,x.category].some(v=>String(v||'').toLowerCase().includes(q)));matched.sort((a,b)=>sort.value==='new'?String(b.reviewed_at||'').localeCompare(String(a.reviewed_at||'')):String(a.reviewed_at||'').localeCompare(String(b.reviewed_at||'')));count.textContent=matched.length+' approved '+(matched.length===1?'report':'reports');list.replaceChildren();if(!matched.length){list.append(node('div','empty',articles.length?'No approved reports match your search.':'No articles have been approved for publication yet. Check back following editorial review.'));return;}for(const a of matched){const card=node('article','news');card.append(node('div','meta',a.category||'Wildlife trafficking'),node('h3',null,a.title));const date=a.published_at?new Date(a.published_at).toLocaleDateString('en-IN',{year:'numeric',month:'short',day:'numeric'}):'Date not supplied';card.append(node('div','details',(a.source||'News source')+'  ·  '+date+(a.source_country?'  ·  '+a.source_country:'')));try{const u=new URL(a.url);if(u.protocol==='https:'||u.protocol==='http:'){const link=node('a',null,'Read original report ↗');link.href=u.href;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}}catch{}list.append(card);}}
search.addEventListener('input',render);sort.addEventListener('change',render);
fetch('data/published.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(data=>{articles=Array.isArray(data)?data.filter(x=>x.status==='published'):[];render()}).catch(()=>{count.textContent='Unavailable';list.replaceChildren(node('div','empty','Could not load approved news. Try refreshing the page.'));});

// Submission links are resolved from the deployed repository, never from user input.
fetch('config.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).then(config=>{
  const repo=String(config.repository||'');
  if(!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) return;
  const href='https://github.com/'+repo+'/issues/new?template=submit-wildlife-news.yml';
  for(const id of ['submitNews','submitSecondary']){const el=document.getElementById(id);if(el){el.href=href;el.target='_blank';el.rel='noopener noreferrer';}}
}).catch(()=>{});
