/* 台股即時報價轉接站：證交所即時報價（mis.twse.com.tw）沒有開放網頁跨網域讀取，
   這支 Cloudflare Worker 代抓後加上允許跨網域的標頭，只給台股趨勢儀表板用。
   GET /?s=2330,2454,00631L,t00   （t00＝加權指數）
   回傳 {代號: {z 成交價, y 昨收, o 開, h 高, l 低, b 最佳買價, a 最佳賣價, t 時間, d 日期}}；
   z 先取這次快照的成交價，沒有就取最近一筆成交；仍是 null 時網頁端改用買賣價或上一筆。 */
const ALLOW = ["https://eason-237588.github.io", "http://127.0.0.1:8768", "http://localhost:8768"];
const CACHE_SEC = 5;

const num = v => { const x = parseFloat(v); return isFinite(x) && x > 0 ? x : null; };
const first = v => num(String(v || "").split("_")[0]);

function cors(origin){
  return {
    "Access-Control-Allow-Origin": ALLOW.includes(origin) ? origin : ALLOW[0],
    "Access-Control-Allow-Methods": "GET",
    "Vary": "Origin",
  };
}

export default {
  async fetch(req, env, ctx){
    const origin = req.headers.get("Origin") || "";
    if(req.method === "OPTIONS") return new Response(null, {headers: cors(origin)});
    const url = new URL(req.url);
    const codes = (url.searchParams.get("s") || "").split(",").map(x => x.trim()).filter(Boolean);
    if(!codes.length || codes.length > 10 || !codes.every(c => /^[0-9A-Za-z]{2,6}$/.test(c)))
      return new Response(JSON.stringify({error: "s 參數要是 1～10 個股票代號，逗號分隔"}), {status: 400, headers: {...cors(origin), "Content-Type": "application/json; charset=utf-8"}});

    // 同一組代號 5 秒內用快取，避免每個開著的頁面都去打證交所
    const key = new Request("https://cache.local/q?s=" + codes.join(","));
    const cache = caches.default;
    let body = await cache.match(key).then(r => r && r.text());
    if(!body){
      const ex = codes.map(c => `tse_${c}.tw`).join("|");   // 代號大小寫要照原樣（00631l 證交所認不得）
      const r = await fetch(`https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${encodeURIComponent(ex)}&json=1&delay=0&_=${Date.now()}`, {
        headers: {"User-Agent": "Mozilla/5.0", "Referer": "https://mis.twse.com.tw/stock/index.jsp", "Accept": "application/json"},
      });
      if(!r.ok) return new Response(JSON.stringify({error: `證交所 HTTP ${r.status}`}), {status: 502, headers: {...cors(origin), "Content-Type": "application/json; charset=utf-8"}});
      const j = await r.json();
      const out = {};
      for(const m of j.msgArray || []){
        if(!m.c) continue;   // 查不到的代號證交所回空殼
        // z 是這次快照的成交價，沒有就用 pz（最近一筆成交）
        out[m.c] = {z: num(m.z) ?? num(m.pz), y: num(m.y), o: num(m.o), h: num(m.h), l: num(m.l), b: first(m.b), a: first(m.a), t: m.t || null, d: m.d || null};
      }
      out._at = Date.now();   // 抓證交所的時間，網頁端可判斷資料新舊
      body = JSON.stringify(out);
      ctx.waitUntil(cache.put(key, new Response(body, {headers: {"Cache-Control": `max-age=${CACHE_SEC}`}})));
    }
    return new Response(body, {headers: {...cors(origin), "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}});
  },
};
