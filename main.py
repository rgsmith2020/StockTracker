import textwrap
import threading
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import customtkinter as ctk
import yfinance as yf

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DEFAULT_TICKERS = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]

MOVER_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "AMD",
    "INTC", "BAC", "F", "GE", "SPY", "QQQ", "PLTR", "NIO", "AAL",
    "CCL", "T", "WFC", "XOM", "CVX", "SOFI", "RIVN", "UBER", "NFLX",
    "DIS", "BABA", "PFE", "MU", "VZ", "C", "JPM", "KO", "SNAP",
]
TOP_N = 10

BG_DARK   = "#1a1a2e"
BG_ROW    = "#2a2a3e"
BG_HEADER = "#1c1c2e"
BG_PANEL  = "#16213e"
GREEN     = "#2ecc71"
RED       = "#e74c3c"
GRAY      = "#aaaaaa"
GRID_CLR  = "#333355"


# ── Console formatting helpers ────────────────────────────────────────────────

def _fmt(val, style: str = "auto") -> str:
    if val is None:
        return "—"
    if style == "price":
        return f"${float(val):,.2f}"
    if style == "pct":
        return f"{float(val) * 100:.2f}%"
    if style == "large":
        v = float(val)
        sign = "-" if v < 0 else ""
        v = abs(v)
        if v >= 1e12:  return f"{sign}${v / 1e12:.2f}T"
        if v >= 1e9:   return f"{sign}${v / 1e9:.2f}B"
        if v >= 1e6:   return f"{sign}${v / 1e6:.2f}M"
        return f"{sign}${v:,.0f}"
    if style == "int":
        return f"{int(val):,}"
    if style == "ratio":
        return f"{float(val):.2f}x"
    return str(val)


def _build_console_text(info: dict) -> str:
    lines: list[str] = []

    def sep(title: str):
        lines.append(f"\n  {'═' * 54}\n  {title}\n  {'─' * 54}\n")

    def row(label: str, key: str, style: str = "auto"):
        val = info.get(key)
        display = _fmt(val, style)
        if len(display) > 62:
            display = display[:59] + "..."
        lines.append(f"  {label:<40} {display}\n")

    sep("COMPANY")
    row("Name",                  "longName")
    row("Symbol",                "symbol")
    row("Exchange",              "exchange")
    row("Quote Type",            "quoteType")
    row("Sector",                "sector")
    row("Industry",              "industry")
    row("Country",               "country")
    row("Website",               "website")

    summary = info.get("longBusinessSummary")
    if summary:
        sep("BUSINESS SUMMARY")
        for ln in textwrap.wrap(summary, width=72):
            lines.append(f"  {ln}\n")

    sep("PRICE")
    row("Current Price",         "currentPrice",            "price")
    row("Previous Close",        "previousClose",           "price")
    row("Open",                  "open",                    "price")
    row("Day High",              "dayHigh",                 "price")
    row("Day Low",               "dayLow",                  "price")
    row("52-Week High",          "fiftyTwoWeekHigh",        "price")
    row("52-Week Low",           "fiftyTwoWeekLow",         "price")
    row("50-Day Average",        "fiftyDayAverage",         "price")
    row("200-Day Average",       "twoHundredDayAverage",    "price")

    sep("MARKET")
    row("Market Cap",            "marketCap",               "large")
    row("Enterprise Value",      "enterpriseValue",         "large")
    row("Volume",                "volume",                  "int")
    row("Avg Volume (3M)",       "averageVolume",           "int")
    row("Avg Volume (10D)",      "averageVolume10days",     "int")
    row("Shares Outstanding",    "sharesOutstanding",       "int")
    row("Float Shares",          "floatShares",             "int")
    row("Beta",                  "beta")

    sep("VALUATION")
    row("Trailing P/E",          "trailingPE")
    row("Forward P/E",           "forwardPE")
    row("Price / Book",          "priceToBook")
    row("Price / Sales (TTM)",   "priceToSalesTrailing12Months")
    row("Trailing EPS",          "trailingEps",             "price")
    row("Forward EPS",           "forwardEps",              "price")
    row("PEG Ratio",             "pegRatio")
    row("EV / Revenue",          "enterpriseToRevenue",     "ratio")
    row("EV / EBITDA",           "enterpriseToEbitda",      "ratio")

    sep("DIVIDENDS")
    row("Dividend Rate",         "dividendRate",            "price")
    row("Dividend Yield",        "dividendYield",           "pct")
    row("Ex-Dividend Date",      "exDividendDate")
    row("Payout Ratio",          "payoutRatio",             "pct")
    row("5-Year Avg Yield",      "fiveYearAvgDividendYield")

    sep("FINANCIALS")
    row("Total Revenue",         "totalRevenue",            "large")
    row("Gross Profits",         "grossProfits",            "large")
    row("EBITDA",                "ebitda",                  "large")
    row("Total Debt",            "totalDebt",               "large")
    row("Total Cash",            "totalCash",               "large")
    row("Debt / Equity",         "debtToEquity")
    row("Revenue / Share",       "revenuePerShare",         "price")
    row("Return on Assets",      "returnOnAssets",          "pct")
    row("Return on Equity",      "returnOnEquity",          "pct")
    row("Gross Margins",         "grossMargins",            "pct")
    row("EBITDA Margins",        "ebitdaMargins",           "pct")
    row("Operating Margins",     "operatingMargins",        "pct")
    row("Profit Margins",        "profitMargins",           "pct")
    row("Revenue Growth",        "revenueGrowth",           "pct")
    row("Earnings Growth",       "earningsGrowth",          "pct")

    sep("ANALYST TARGETS")
    row("# of Analysts",         "numberOfAnalystOpinions", "int")
    row("Recommendation",        "recommendationKey")
    row("Mean Score (1=Buy…5)",  "recommendationMean")
    row("Target High",           "targetHighPrice",         "price")
    row("Target Mean",           "targetMeanPrice",         "price")
    row("Target Median",         "targetMedianPrice",       "price")
    row("Target Low",            "targetLowPrice",          "price")

    return "".join(lines)


# ── History window ────────────────────────────────────────────────────────────

class HistoryWindow(ctk.CTkToplevel):
    PERIODS = [("1mo", "1M"), ("3mo", "3M"), ("6mo", "6M"), ("1y", "1Y"), ("2y", "2Y")]

    def __init__(self, parent, ticker: str):
        super().__init__(parent)
        self.ticker = ticker
        self.title(f"{ticker} — Price History")
        self.geometry("900x860")
        self.minsize(640, 580)
        self._canvas_widget  = None
        self._current_hist   = None
        self._current_period = "3mo"
        self._build_ui()
        self._load("3mo")
        threading.Thread(target=self._fetch_info, daemon=True).start()

    def _build_ui(self):
        # Period selector row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))

        self.title_lbl = ctk.CTkLabel(
            top, text=f"{self.ticker}  —  Price History",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title_lbl.pack(side="left")

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(side="right")

        self._chart_toggle = ctk.CTkSegmentedButton(
            btn_frame, values=["Bar", "Candle"], width=130,
            command=self._on_chart_type,
        )
        self._chart_toggle.set("Bar")
        self._chart_toggle.pack(side="left", padx=(0, 12))

        self._period_btns: dict[str, ctk.CTkButton] = {}
        for period, label in self.PERIODS:
            btn = ctk.CTkButton(
                btn_frame, text=label, width=48,
                command=lambda p=period: self._load(p),
            )
            btn.pack(side="left", padx=2)
            self._period_btns[period] = btn

        # Chart
        self.chart_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=8)
        self.chart_frame.pack(fill="both", expand=True, padx=16, pady=(4, 0))

        self.chart_status = ctk.CTkLabel(self, text="Loading chart…", text_color=GRAY)
        self.chart_status.pack(pady=(2, 6))

        # Console
        console_hdr = ctk.CTkFrame(self, fg_color="transparent")
        console_hdr.pack(fill="x", padx=16, pady=(2, 2))
        ctk.CTkLabel(
            console_hdr, text="Data Console",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")
        self.console_status = ctk.CTkLabel(
            console_hdr, text="fetching…", text_color=GRAY,
            font=ctk.CTkFont(size=11),
        )
        self.console_status.pack(side="left", padx=10)

        self.console = ctk.CTkTextbox(
            self, height=240, corner_radius=8,
            fg_color="#0d1117", text_color="#c9d1d9",
            font=("Courier New", 10),
            scrollbar_button_color=BG_HEADER,
        )
        self.console.pack(fill="x", padx=16, pady=(0, 14))
        self.console.insert("end", "  Loading stock data…\n")
        self.console.configure(state="disabled")

    # ── Chart ─────────────────────────────────────────────────────────────────

    def _load(self, period: str):
        self.chart_status.configure(text="Loading chart…")
        for btn in self._period_btns.values():
            btn.configure(state="disabled")
        threading.Thread(target=self._fetch_chart, args=(period,), daemon=True).start()

    def _fetch_chart(self, period: str):
        try:
            hist = yf.Ticker(self.ticker).history(period=period)
            self.after(0, lambda: self._plot(hist, period))
        except Exception as exc:
            self.after(0, lambda e=exc: self.chart_status.configure(text=f"Error: {e}"))
        finally:
            self.after(0, lambda: [b.configure(state="normal") for b in self._period_btns.values()])

    def _on_chart_type(self, _value: str):
        if self._current_hist is not None:
            self._plot(self._current_hist, self._current_period)

    def _plot(self, hist, period: str):
        self._current_hist   = hist
        self._current_period = period

        if self._canvas_widget:
            self._canvas_widget.destroy()
            self._canvas_widget = None

        if hist.empty:
            self.chart_status.configure(text="No data returned for this period.")
            return

        closes = hist["Close"].dropna()
        dates  = closes.index
        n      = len(dates)

        fig = Figure(facecolor=BG_DARK)
        ax  = fig.add_subplot(111, facecolor=BG_DARK)

        chart_type = self._chart_toggle.get()
        if chart_type == "Candle":
            self._draw_candles(ax, hist)
            ylabel = "Price (USD)"
        else:
            self._draw_bars(ax, closes)
            ylabel = "Close Price (USD)"

        step  = max(1, n // 8)
        ticks = list(range(0, n, step))
        ax.set_xticks(ticks)
        ax.set_xticklabels(
            [dates[i].strftime("%b %d") for i in ticks],
            color=GRAY, fontsize=8, rotation=30, ha="right",
        )
        ax.tick_params(axis="y", colors=GRAY)
        ax.set_ylabel(ylabel, color=GRAY, fontsize=9)
        ax.set_title(
            f"{self.ticker}  {chart_type} Chart  ({period})",
            color="white", fontsize=11, pad=10,
        )
        ax.grid(axis="y", color=GRID_CLR, linewidth=0.5, alpha=0.8)
        for spine in ax.spines.values():
            spine.set_color("#444466")
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)
        self._canvas_widget = widget

        last_close = float(closes.iloc[-1])
        self.chart_status.configure(text=f"{n} trading days  •  last close ${last_close:,.2f}")

    def _draw_bars(self, ax, closes):
        prices = closes.values
        colors = [GREEN if i == 0 or prices[i] >= prices[i - 1] else RED for i in range(len(prices))]
        ax.bar(range(len(prices)), prices, color=colors, width=0.8, alpha=0.6)
        ax.plot(range(len(prices)), prices, color="#00d4ff", linewidth=1.5,
                marker="o", markersize=2.5, markerfacecolor="white", markeredgewidth=0, zorder=3)

    def _draw_candles(self, ax, hist):
        opens  = hist["Open"].values
        highs  = hist["High"].values
        lows   = hist["Low"].values
        closes = hist["Close"].values
        price_range = highs.max() - lows.min()
        min_body    = price_range * 0.003   # floor so doji candles stay visible

        for i in range(len(closes)):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            color    = GREEN if c >= o else RED
            body_bot = min(o, c)
            body_h   = max(abs(c - o), min_body)
            ax.vlines(i, l, h, color=color, linewidth=0.9, zorder=1)
            ax.bar(i, body_h, bottom=body_bot, color=color, width=0.6, zorder=2)

    # ── Console ───────────────────────────────────────────────────────────────

    def _fetch_info(self):
        try:
            info = yf.Ticker(self.ticker).info
            name = info.get("longName") or ""
            text = _build_console_text(info)
            self.after(0, lambda: self._populate_console(text, name))
        except Exception as exc:
            self.after(0, lambda e=exc: self.console_status.configure(text=f"Error: {e}"))

    def _populate_console(self, text: str, name: str = ""):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.insert("end", text)
        self.console.configure(state="disabled")
        self.console_status.configure(text="loaded")
        if name:
            self.title_lbl.configure(text=f"{self.ticker}  —  {name}  —  Price History")
            self.title(f"{self.ticker} — {name}")


# ── Main app ──────────────────────────────────────────────────────────────────

class StockApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Stock Price Viewer")
        self.geometry("1320x600")
        self.minsize(1020, 440)
        self.tickers: list[str] = []
        self.rows:    dict[str, dict] = {}
        self._mover_rows: list[dict] = []
        self._build_ui()
        for t in DEFAULT_TICKERS:
            self._add_row(t)
        self.refresh()

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            top_bar, text="Stock Price Viewer",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")

        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.pack(fill="x", padx=16, pady=4)
        self.ticker_entry = ctk.CTkEntry(
            add_frame, placeholder_text="Ticker symbol (e.g. NVDA)", width=230,
        )
        self.ticker_entry.pack(side="left", padx=(0, 8))
        self.ticker_entry.bind("<Return>", lambda _: self._add_ticker())
        ctk.CTkButton(add_frame, text="Add", width=80, command=self._add_ticker).pack(side="left")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=4)
        self._build_watchlist(content)
        self._build_movers_panel(content)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=12)
        self.refresh_btn = ctk.CTkButton(
            bottom, text="Refresh Prices", width=150, command=self.refresh,
        )
        self.refresh_btn.pack(side="left")
        self.status_lbl = ctk.CTkLabel(bottom, text="Click Refresh to load prices", text_color=GRAY)
        self.status_lbl.pack(side="left", padx=16)

    def _build_watchlist(self, parent):
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        hdr = ctk.CTkFrame(left, fg_color=BG_HEADER, corner_radius=6)
        hdr.pack(fill="x", pady=(0, 2))
        for text, width in [
            ("Symbol", 110), ("Price", 120), ("Change", 110),
            ("% Change", 110), ("Volume", 120), ("Mean Score", 120), ("", 180),
        ]:
            ctk.CTkLabel(hdr, text=text, width=width, anchor="w",
                         font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8, pady=6)

        self.list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True)

    def _build_movers_panel(self, parent):
        right = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=10, width=310)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="Top Movers by Volume",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12, pady=(12, 4), anchor="w")

        hdr = ctk.CTkFrame(right, fg_color=BG_HEADER, corner_radius=4)
        hdr.pack(fill="x", padx=8, pady=(0, 4))
        for text, width in [("#", 28), ("Symbol", 70), ("Volume", 100), ("% Chg", 78)]:
            ctk.CTkLabel(hdr, text=text, width=width, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=4, pady=4)

        rows_frame = ctk.CTkFrame(right, fg_color="transparent")
        rows_frame.pack(fill="both", expand=True, padx=8)

        for _ in range(TOP_N):
            row = ctk.CTkFrame(rows_frame, fg_color=BG_ROW, corner_radius=4)
            row.pack(fill="x", pady=2)
            rank_lbl = ctk.CTkLabel(row, text="—", width=28,  anchor="w", font=ctk.CTkFont(size=11))
            sym_lbl  = ctk.CTkLabel(row, text="—", width=70,  anchor="w", font=ctk.CTkFont(size=11, weight="bold"))
            vol_lbl  = ctk.CTkLabel(row, text="—", width=100, anchor="w", font=ctk.CTkFont(size=11))
            pct_lbl  = ctk.CTkLabel(row, text="—", width=78,  anchor="w", font=ctk.CTkFont(size=11))
            for lbl in (rank_lbl, sym_lbl, vol_lbl, pct_lbl):
                lbl.pack(side="left", padx=4, pady=5)
            self._mover_rows.append({"rank": rank_lbl, "symbol": sym_lbl, "volume": vol_lbl, "pct": pct_lbl})

        self.movers_status = ctk.CTkLabel(right, text="", text_color=GRAY, font=ctk.CTkFont(size=10))
        self.movers_status.pack(pady=(4, 8))

    # ── Watchlist row management ──────────────────────────────────────────────

    def _add_row(self, ticker: str):
        ticker = ticker.upper()
        if ticker in self.rows:
            return
        self.tickers.append(ticker)

        row = ctk.CTkFrame(self.list_frame, fg_color=BG_ROW, corner_radius=6)
        row.pack(fill="x", pady=2)

        lbls: dict[str, ctk.CTkLabel] = {}
        for key, width, initial in [
            ("symbol", 110, ticker), ("price",  120, "—"),
            ("change", 110, "—"),    ("pct",    110, "—"),
            ("volume", 120, "—"),    ("score",  120, "—"),
        ]:
            font = ctk.CTkFont(weight="bold") if key == "symbol" else ctk.CTkFont()
            lbl  = ctk.CTkLabel(row, text=initial, width=width, anchor="w", font=font)
            lbl.pack(side="left", padx=8, pady=8)
            lbls[key] = lbl

        ctk.CTkButton(row, text="History", width=75,
                      command=lambda t=ticker: self._open_history(t)).pack(side="left", padx=(4, 2))
        ctk.CTkButton(row, text="Remove", width=75,
                      fg_color="#922b21", hover_color="#6e1f18",
                      command=lambda t=ticker: self._remove_ticker(t)).pack(side="left", padx=(2, 4))

        self.rows[ticker] = {"frame": row, "labels": lbls}

    def _remove_ticker(self, ticker: str):
        if ticker in self.rows:
            self.rows[ticker]["frame"].destroy()
            del self.rows[ticker]
        if ticker in self.tickers:
            self.tickers.remove(ticker)

    def _open_history(self, ticker: str):
        HistoryWindow(self, ticker).focus()

    def _add_ticker(self):
        raw = self.ticker_entry.get().strip().upper()
        self.ticker_entry.delete(0, "end")
        if not raw or raw in self.rows:
            return
        self._add_row(raw)
        threading.Thread(target=self._fetch_ticker, args=(raw,), daemon=True).start()

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        self.refresh_btn.configure(state="disabled", text="Refreshing...")
        self.status_lbl.configure(text="Fetching prices...")
        self.movers_status.configure(text="Scanning movers…")
        threading.Thread(target=self._fetch_all, daemon=True).start()
        threading.Thread(target=self._fetch_movers, daemon=True).start()

    def _fetch_all(self):
        tickers = list(self.tickers)
        threads = [threading.Thread(target=self._fetch_ticker, args=(t,), daemon=True) for t in tickers]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.after(0, self._done_refreshing)

    def _fetch_ticker(self, ticker: str):
        t_obj = yf.Ticker(ticker)
        try:
            hist    = t_obj.history(period="5d")
            if hist.empty:
                self.after(0, lambda t=ticker: self._mark_error(t, "No data"))
                return
            closes  = hist["Close"].dropna()
            volumes = hist["Volume"].dropna()
            today   = float(closes.iloc[-1])
            prev    = float(closes.iloc[-2]) if len(closes) >= 2 else today
            vol     = float(volumes.iloc[-1]) if not volumes.empty else 0.0
            change  = today - prev
            pct     = (change / prev * 100) if prev else 0.0
            self.after(0, lambda: self._update_row(ticker, today, change, pct, vol))
        except Exception as exc:
            self.after(0, lambda e=exc, t=ticker: self._mark_error(t, str(e)))
        try:
            score = t_obj.info.get("recommendationMean")
            if score is not None:
                self.after(0, lambda s=float(score), t=ticker: self._update_mean_score(t, s))
        except Exception:
            pass

    def _fetch_movers(self):
        results: list[dict] = []
        lock = threading.Lock()

        def fetch_one(ticker: str):
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if hist.empty:
                    return
                closes  = hist["Close"].dropna()
                volumes = hist["Volume"].dropna()
                if closes.empty or volumes.empty:
                    return
                today = float(closes.iloc[-1])
                prev  = float(closes.iloc[-2]) if len(closes) >= 2 else today
                vol   = float(volumes.iloc[-1])
                pct   = ((today - prev) / prev * 100) if prev else 0.0
                with lock:
                    results.append({"ticker": ticker, "volume": vol, "pct": pct})
            except Exception:
                pass

        threads = [threading.Thread(target=fetch_one, args=(t,), daemon=True) for t in MOVER_UNIVERSE]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        top = sorted(results, key=lambda x: x["volume"], reverse=True)[:TOP_N]
        self.after(0, lambda: self._update_movers(top))

    # ── UI updates (main thread only) ─────────────────────────────────────────

    def _update_row(self, ticker: str, price: float, change: float, pct: float, volume: float):
        if ticker not in self.rows:
            return
        lbls  = self.rows[ticker]["labels"]
        color = GREEN if change >= 0 else RED
        sign  = "+" if change >= 0 else ""
        lbls["price"].configure(text=f"${price:,.2f}")
        lbls["change"].configure(text=f"{sign}{change:,.2f}", text_color=color)
        lbls["pct"].configure(text=f"{sign}{pct:.2f}%", text_color=color)
        lbls["volume"].configure(text=f"{int(volume):,}")

    def _update_mean_score(self, ticker: str, score: float):
        if ticker not in self.rows:
            return
        if score <= 1.5:
            label, color = "Strong Buy", "#27ae60"
        elif score <= 2.5:
            label, color = "Buy",        GREEN
        elif score <= 3.5:
            label, color = "Hold",       "#f39c12"
        elif score <= 4.5:
            label, color = "Sell",       RED
        else:
            label, color = "Strong Sell", "#922b21"
        self.rows[ticker]["labels"]["score"].configure(
            text=f"{score:.1f}  {label}", text_color=color,
        )

    def _update_movers(self, top: list[dict]):
        for i, row_lbls in enumerate(self._mover_rows):
            if i < len(top):
                entry = top[i]
                pct   = entry["pct"]
                color = GREEN if pct >= 0 else RED
                sign  = "+" if pct >= 0 else ""
                row_lbls["rank"].configure(text=f"#{i + 1}")
                row_lbls["symbol"].configure(text=entry["ticker"])
                row_lbls["volume"].configure(text=f"{entry['volume'] / 1_000_000:.1f}M")
                row_lbls["pct"].configure(text=f"{sign}{pct:.2f}%", text_color=color)
            else:
                for key in ("rank", "symbol", "volume", "pct"):
                    row_lbls[key].configure(text="—", text_color="white")
        self.movers_status.configure(text=f"Updated {datetime.now().strftime('%I:%M %p')}")

    def _mark_error(self, ticker: str, message: str):
        if ticker not in self.rows:
            return
        for key in ("price", "change", "pct", "volume"):
            self.rows[ticker]["labels"][key].configure(text="ERR", text_color="#e67e22")
        self.status_lbl.configure(text=f"{ticker}: {message}")

    def _done_refreshing(self):
        now = datetime.now().strftime("%I:%M:%S %p")
        self.status_lbl.configure(text=f"Last updated: {now}")
        self.refresh_btn.configure(state="normal", text="Refresh Prices")


if __name__ == "__main__":
    app = StockApp()
    app.mainloop()
