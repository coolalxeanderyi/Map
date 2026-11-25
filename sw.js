// 離線也能打開：網頁本身、美食清單、站牌清單會存一份在手機裡；即時公車一定要有網路。
const CACHE='tucheng-v2';
const CORE=['./','index.html','food.json','manifest.json','icon.svg','icon-180.png','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
const LIVE=/tcgbusfs\.blob\.core\.windows\.net|nominatim|photon\.komoot|translate\.google|api\.github\.com|api\.open-meteo/;
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(LIVE.test(url.host+url.pathname))return; // 即時資料：只走網路
  if(url.pathname.endsWith('admin.html'))return;
  // 先上網拿最新的，拿不到才用手機裡存的
  e.respondWith(fetch(req).then(res=>{
    if(res.ok||res.type==='opaque'){const copy=res.clone();const key=url.origin===location.origin?url.pathname.replace(/\/$/,'/')+'':req.url.split('?')[0];caches.open(CACHE).then(c=>c.put(key,copy))}
    return res;
  }).catch(async()=>{
    const c=await caches.open(CACHE);
    const key=url.origin===location.origin?url.pathname:req.url.split('?')[0];
    return (await c.match(key))||(await c.match(req,{ignoreSearch:true}))||(req.mode==='navigate'?(await c.match('index.html'))||(await c.match('./')):Response.error());
  }));
});
