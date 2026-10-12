"""台股趨勢儀表板・實際進出紀錄

規則跟儀表板 index.html 一模一樣：加權指數日線 Range Filter 取樣 15、倍數 4，
轉多就用收盤價買進台灣 50 正 2（00631L），轉空就收盤賣出拿現金。

每次開工執行：
    python 更新紀錄.py
1. 從證交所抓加權指數日線、正 2 與 0050 日成交（過去月份存在 快取/，只重抓當月）
2. 照規則算部位，把「上次紀錄之後」的進出追加到 進出紀錄.csv（只追加、不改舊列）
3. 印出總表與逐筆明細，重畫 績效曲線.png（儀表板「曲線圖」按鈕讀這張）

報酬計算：
- 正 2 在 2026/03/24→03/31 做過 1 拆 22（發行股數 1.67 億→36.6 億）。逐日串收盤價，
  停牌日價值不動；恢復交易那天跟停牌前最後一個收盤比，變動超過一倍就當成分割、乘回整數倍數。
- 比較用的「0050 抱著」把除息加回去（證交所除權息資料的 除息前收盤÷參考價）。
- 未扣手續費與證交稅（一買一賣約 0.18%）。
只用 Python 內建模組；畫圖用 matplotlib。
"""
import csv, json, os, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone

START = "2026-01-02"        # 起算日（使用者 2026-10-12 同意先從今年第一個交易日起算）
PER, MULT = 15, 4
ETF, BENCH = "00631L", "0050"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "進出紀錄.csv")
CACHE = os.path.join(HERE, "快取")
PNG = os.path.join(HERE, "績效曲線.png")
TZ = timezone(timedelta(hours=8))
TODAY = datetime.now(TZ).date()
COLS = ["日期", "動作", "部位", "加權指數", "正2收盤", "備註"]

# ============ 證交所 ============
_last = [0.0]
def twse(path):
    """證交所短時間大量請求會故意放慢，請求間隔 1.2 秒；失敗重試三次"""
    for k in range(3):
        w = _last[0] + 1.2 - time.time()
        if w > 0: time.sleep(w)
        _last[0] = time.time()
        try:
            req = urllib.request.Request("https://www.twse.com.tw/rwd/zh" + path, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:
            print(f"  證交所請求失敗（第 {k+1} 次）：{e}")
            time.sleep(5)
    raise SystemExit("證交所連不上，稍後再跑")

def roc(s):  # 115/10/01 → 2026-10-01
    y, m, d = s.strip().split("/"); return f"{int(y)+1911}-{m}-{d}"
num = lambda s: float(str(s).replace(",", ""))

def months(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield y, m
        m += 1
        if m > 12: y, m = y + 1, 1

def cached(name, path, cur):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, name + ".json")
    if not cur and os.path.exists(f):
        return json.load(open(f, encoding="utf-8"))
    j = twse(path)
    if not cur and j.get("stat") == "OK":
        json.dump(j, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    return j

def index_bars(a, b):
    B = []
    for y, m in months(a, b):
        cur = (y, m) == (TODAY.year, TODAY.month)
        j = cached(f"指數_{y}{m:02d}", f"/TAIEX/MI_5MINS_HIST?response=json&date={y}{m:02d}01", cur)
        for r in j.get("data") or []:
            B.append(dict(d=roc(r[0]), o=num(r[1]), h=num(r[2]), l=num(r[3]), c=num(r[4])))
    return B

def stock_close(code, a, b):
    out = {}
    for y, m in months(a, b):
        cur = (y, m) == (TODAY.year, TODAY.month)
        j = cached(f"{code}_{y}{m:02d}", f"/afterTrading/STOCK_DAY?response=json&stockNo={code}&date={y}{m:02d}01", cur)
        for r in j.get("data") or []:
            try: out[roc(r[0])] = num(r[6])
            except ValueError: pass   # 停牌日收盤是 --
    return out

def dividends(code, a, b):
    """除息日 → 除息前收盤÷參考價"""
    j = twse(f"/exRight/TWT49U?response=json&startDate={a:%Y%m%d}&endDate={b:%Y%m%d}")
    out = {}
    for r in j.get("data") or []:
        if r[1] == code:
            y, m, d = r[0].replace("年", "/").replace("月", "/").replace("日", "").split("/")
            out[f"{int(y)+1911}-{m}-{d}"] = num(r[3]) / num(r[4])
    return out

# ============ Range Filter：逐行照 index.html calcRF ============
def pine_ma(src, n, alpha):
    out = [None] * len(src); prev = None; s = 0; cnt = 0
    for i, v in enumerate(src):
        if v is None: out[i] = prev; continue
        if prev is None:
            s += v; cnt += 1
            if cnt == n: prev = s / n; out[i] = prev
        else: prev = alpha * v + (1 - alpha) * prev; out[i] = prev
    return out
ema = lambda s, n: pine_ma(s, n, 2 / (n + 1))
rma = lambda s, n: pine_ma(s, n, 1 / n)

def calc_rf(B, per, mult, atr_len=12, atr_mult=1.5):
    n = len(B); src = [(b["h"] + b["l"]) / 2 for b in B]
    diff = [None] + [abs(src[i] - src[i-1]) for i in range(1, n)]
    sm = [None if v is None else v * mult for v in ema(ema(diff, per), per * 2 - 1)]
    filt = [None] * n; prev = None
    for i in range(n):
        x, r = src[i], sm[i]
        if r is None: prev = None; continue
        pv = 0 if prev is None else prev
        filt[i] = prev = (pv if x - r < pv else x - r) if x > pv else (pv if x + r > pv else x + r)
    tr = [B[0]["h"] - B[0]["l"]] + [max(B[i]["h"] - B[i]["l"], abs(B[i]["h"] - B[i-1]["c"]), abs(B[i]["l"] - B[i-1]["c"])) for i in range(1, n)]
    atr = rma(tr, atr_len)
    pos = [0] * n; up = dn = 0; ci = None; cur = 0; first = None
    for i in range(n):
        f = filt[i]; pf = filt[i-1] if i else None
        if f is not None and pf is not None:
            up = up + 1 if f > pf else (0 if f < pf else up)
            dn = dn + 1 if f < pf else (0 if f > pf else dn)
        s = src[i]; ps = src[i-1] if i else None; moved = ps is not None and s != ps
        a = atr[i]; c = B[i]["c"]
        ls = f is not None and s > f and moved and up > 0 and a is not None and c > c - a * atr_mult
        ss = f is not None and s < f and moved and dn > 0 and a is not None and c < c + a * atr_mult
        pci = ci; ci = 1 if ls else (-1 if ss else pci)
        if ls and pci == -1: cur = 1; first = first or (i, 1)
        elif ss and pci == 1: cur = -1; first = first or (i, -1)
        pos[i] = cur
    if first:   # 第一次翻轉前補上相反部位（同 index.html v1.0.3）
        for i in range(first[0]): pos[i] = -first[1]
    return pos, 6 * per

# ============ 紀錄檔 ============
def load_log():
    if not os.path.exists(LOG): return []
    with open(LOG, encoding="utf-8-sig") as f: return list(csv.DictReader(f))

def append_rows(rows):
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.DictWriter(f, COLS)
        if new: w.writeheader()
        w.writerows(rows)

# ============ 報酬 ============
def chain(px, idx, div, days, lev):
    """逐日累乘報酬。停牌日（沒有收盤價）價值不動；分割日乘回整數倍數。idx、lev 用來判斷分割倍數"""
    g = [1.0]; lastp = px.get(days[0]); lastd = days[0]
    for d in days[1:]:
        if d in px and lastp is not None:
            r = px[d] / lastp * div.get(d, 1.0)
            if not 0.5 < r < 2:   # 分割：先扣掉停牌期間指數漲跌×槓桿再取整數（直接取會得到 23）
                e = r / (1 + lev * (idx[d] / idx[lastd] - 1))
                r *= round(1 / e) if e < 1 else 1 / round(e)
            g.append(g[-1] * r)
        else: g.append(g[-1])
        if d in px: lastp, lastd = px[d], d
    return g

# ============ 曲線 ============
def draw(days, eq, bh, holds, total, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt, matplotlib.dates as mdates
    plt.rcParams["font.family"] = ["Microsoft JhengHei"]; plt.rcParams["axes.unicode_minus"] = False
    INK, MUTED, GRID, LINE, BG = "#1f1f1e", "#6b6a66", "#e6e5e1", "#d62a2a", "#fcfcfb"
    xs = [datetime.strptime(d, "%Y-%m-%d") for d in days]
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=BG); ax.set_facecolor(BG)
    for a, b in holds:
        ax.axvspan(datetime.strptime(a, "%Y-%m-%d"), datetime.strptime(b, "%Y-%m-%d"), color="#d62a2a", alpha=0.06, lw=0)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.plot(xs, [(v - 1) * 100 for v in bh], color="#8a8a86", lw=1.3, ls="--", label="0050 抱著（含配息）")
    ax.plot(xs, [(v - 1) * 100 for v in eq], color=LINE, lw=1.8, label="策略（正 2 或空手）")
    ax.plot([xs[-1]], [(eq[-1] - 1) * 100], "o", ms=8, color=LINE, mec=BG, mew=2)
    # 兩個尾端數字太接近時上下錯開，免得疊字
    e1, b1 = (eq[-1] - 1) * 100, (bh[-1] - 1) * 100
    lo_, hi_ = min(min(eq), min(bh)), max(max(eq), max(bh)); gap = (hi_ - lo_) * 100 * 0.06
    sep = 0 if abs(e1 - b1) >= gap else (gap - abs(e1 - b1)) / 2
    up_e = 1 if e1 >= b1 else -1
    off = ax.transData + matplotlib.transforms.ScaledTranslation(8/72, 0, fig.dpi_scale_trans)   # 往右 8 點
    ax.text(xs[-1], e1 + up_e * sep, f"{e1:+.1f}%", transform=off, va="center", color=INK, fontsize=10)
    ax.text(xs[-1], b1 - up_e * sep, f"{b1:+.1f}%", transform=off, va="center", color=MUTED, fontsize=9)
    ax.set_title(f"台股趨勢・實際進出績效　起算 {START.replace('-', '/')}　合計 {total:+.2f}%", loc="left", color=INK, fontsize=11)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d")); ax.margins(x=0.04)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    fig.text(0.01, 0.005, "每日收盤的「已實現＋持有中浮動」累計報酬（複利）。紅底＝持有正 2。未扣手續費與證交稅。", color=MUTED, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(path, dpi=130, facecolor=BG); plt.close(fig)

# ============ 主程式 ============
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    s0 = date.fromisoformat(START)
    warm_from = date(s0.year - 1, s0.month, 1)    # 往前多抓一年暖機
    print("抓加權指數日線（過去月份讀快取）")
    B = index_bars(warm_from, TODAY)
    pos, warm = calc_rf(B, PER, MULT)
    idx = {b["d"]: b["c"] for b in B}
    print("抓正 2、0050 日成交與除息")
    etf = stock_close(ETF, s0, TODAY); bench = stock_close(BENCH, s0, TODAY)
    div = dividends(BENCH, s0, TODAY)
    last_d = B[-1]["d"]

    # ---- 追加新列 ----
    rows = load_log(); added = []
    st = lambda p: "持有正2" if p == 1 else "空手"
    i0 = next(i for i, b in enumerate(B) if b["d"] >= START)
    def row(i, act, note=""):
        d = B[i]["d"]
        return dict(日期=d, 動作=act, 部位=st(pos[i]), 加權指數=f"{B[i]['c']:.2f}",
                    正2收盤=f"{etf[d]:.2f}" if d in etf else "", 備註=note)
    if not rows:
        added.append(row(i0, "起算持有" if pos[i0] == 1 else "起算空手", "起算時的部位，以起算日收盤計"))
        after = B[i0]["d"]
    else:
        after = rows[-1]["日期"]
    for i in range(i0 + 1, len(B)):
        if B[i]["d"] <= after or pos[i] == pos[i-1]: continue
        added.append(row(i, "買進" if pos[i] == 1 else "賣出"))
    # 資料源重算後部位跟紀錄最後一列不同 → 記一筆校正
    cur_state = (added or rows)[-1]["部位"]
    if cur_state != st(pos[-1]):
        added.append(row(len(B) - 1, "校正", "資料源重算後部位不同，校正"))
    if added: append_rows(added)
    rows = load_log()

    # ---- 績效：照紀錄檔的部位逐日算 ----
    days = [b["d"] for b in B if b["d"] >= START]
    state = {}; k = 0; curp = None
    for d in days:
        while k < len(rows) and rows[k]["日期"] <= d: curp = rows[k]["部位"]; k += 1
        state[d] = curp
    g_etf = chain(etf, idx, {}, days, 2); g_bh = chain(bench, idx, div, days, 1)
    eq = [1.0]
    for i in range(1, len(days)):
        eq.append(eq[-1] * (g_etf[i] / g_etf[i-1] if state[days[i-1]] == "持有正2" else 1.0))
    # 逐筆
    trades = []; ent = None
    for r in rows:
        if r["部位"] == "持有正2" and ent is None: ent = r
        elif r["部位"] == "空手" and ent is not None: trades.append((ent, r)); ent = None
    di = {d: i for i, d in enumerate(days)}
    gr = lambda a, b: g_etf[di[b]] / g_etf[di[a]] - 1
    closed = [(a, b, gr(a["日期"], b["日期"])) for a, b in trades]
    realized = 1.0
    for *_, r in closed: realized *= 1 + r
    flo = gr(ent["日期"], last_d) if ent else None
    total = (eq[-1] - 1) * 100
    win = sum(1 for *_, r in closed if r > 0)

    print(f"\n資料到 {last_d.replace('-', '/')} 收盤　本次新增 {len(added)} 筆　（未扣手續費與證交稅）\n")
    print("| 起算 | 已平倉 | 賺／賠 | 已實現 | 持有中 | 浮動 | 合計 | 0050 抱著同期 | 正 2 抱著同期 |")
    print("|---|---|---|---|---|---|---|---|---|")
    hold = f"持有正 2，{ent['日期'][5:].replace('-', '/')} 進場，指數 {float(ent['加權指數']):,.0f}、正 2 {ent['正2收盤']}" if ent else "空手"
    print(f"| {START.replace('-', '/')} | {len(closed)} 筆 | {win} 賺 {len(closed)-win} 賠 | {(realized-1)*100:+.2f}% | {hold} | "
          f"{'—' if flo is None else f'{flo*100:+.2f}%'} | **{total:+.2f}%** | {(g_bh[-1]-1)*100:+.2f}% | {(g_etf[-1]-1)*100:+.2f}% |")
    print("\n逐筆明細")
    print("| # | 進場日 | 指數 | 正 2 | 出場日 | 指數 | 正 2 | 報酬 | 累計 |")
    print("|---|---|---|---|---|---|---|---|---|")
    acc = 1.0
    for n, (a, b, r) in enumerate(closed, 1):
        acc *= 1 + r
        print(f"| {n} | {a['日期'][5:].replace('-','/')}{'＊' if a['動作'].startswith('起算') else ''} | {float(a['加權指數']):,.0f} | {a['正2收盤']} | "
              f"{b['日期'][5:].replace('-','/')} | {float(b['加權指數']):,.0f} | {b['正2收盤']} | {r*100:+.2f}% | {(acc-1)*100:+.2f}% |")
    if ent:
        print(f"| 持有中 | {ent['日期'][5:].replace('-','/')} | {float(ent['加權指數']):,.0f} | {ent['正2收盤']} | — | {idx[last_d]:,.0f} | {etf.get(last_d, '—')} | 浮動 {flo*100:+.2f}% | {total:+.2f}% |")
    print("\n＊＝起算時已有的部位。正 2 價格是證交所原始收盤，2026/03 分割前後價位不同，報酬已換算。")

    holds = []; hs = None
    for d in days:
        if state[d] == "持有正2" and hs is None: hs = d
        if state[d] != "持有正2" and hs is not None: holds.append((hs, d)); hs = None
    if hs: holds.append((hs, days[-1]))
    draw(days, eq, g_bh, holds, total, PNG)
    print(f"\n曲線圖已更新：{PNG}")
