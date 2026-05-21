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

# Universe scanned to build the "Top Movers by Volume" panel
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


# ── History window ────────────────────────────────────────────────────────────

class HistoryWindow(ctk.CTkToplevel):
    PERIODS = [("1mo", "1M"), ("3mo", "3M"), ("6mo", "6M"), ("1y", "1Y"), ("2y", "2Y")]

    def __init__(self, parent, ticker: str):
        super().__init__(parent)
        self.ticker = ticker
        self.title(f"{ticker} — Price History")
        self.geometry("860x500")
        self.minsize(600, 380)
        self._canvas_widget = None
        self._build_ui()
        self._load("3mo")

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            top, text=f"{self.ticker}  —  Price History",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(side="right")

        self._period_btns: dict[str, ctk.CTkButton] = {}
        for period, label in self.PERIODS:
            btn = ctk.CTkButton(
                btn_frame, text=label, width=48,
                command=lambda p=period: self._load(p),
            )
            btn.pack(side="left", padx=2)
            self._period_btns[period] = btn

        self.chart_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=8)
        self.chart_frame.pack(fill="both", expand=True, padx=16, pady=4)

        self.status_lbl = ctk.CTkLabel(self, text="Loading…", text_color=GRAY)
        self.status_lbl.pack(pady=(2, 10))

    def _load(self, period: str):
        self.status_lbl.configure(text="Loading…")
        for btn in self._period_btns.values():
            btn.configure(state="disabled")
        threading.Thread(target=self._fetch, args=(period,), daemon=True).start()

    def _fetch(self, period: str):
        try:
            hist = yf.Ticker(self.ticker).history(period=period)
            self.after(0, lambda: self._plot(hist, period))
        except Exception as exc:
            self.after(0, lambda e=exc: self.status_lbl.configure(text=f"Error: {e}"))
        finally:
            self.after(0, self._re_enable_btns)

    def _re_enable_btns(self):
        for btn in self._period_btns.values():
            btn.configure(state="normal")

    def _plot(self, hist, period: str):
        if self._canvas_widget:
            self._canvas_widget.destroy()
            self._canvas_widget = None

        if hist.empty:
            self.status_lbl.configure(text="No data returned for this period.")
            return

        closes = hist["Close"].dropna()
        dates  = closes.index
        prices = closes.values

        colors = [
            GREEN if i == 0 or prices[i] >= prices[i - 1] else RED
            for i in range(len(prices))
        ]

        fig = Figure(facecolor=BG_DARK)
        ax  = fig.add_subplot(111, facecolor=BG_DARK)

        ax.bar(range(len(prices)), prices, color=colors, width=0.8)

        n    = len(dates)
        step = max(1, n // 8)
        ticks = list(range(0, n, step))
        ax.set_xticks(ticks)
        ax.set_xticklabels(
            [dates[i].strftime("%b %d") for i in ticks],
            color=GRAY, fontsize=8, rotation=30, ha="right",
        )
        ax.tick_params(axis="y", colors=GRAY)
        ax.set_ylabel("Close Price (USD)", color=GRAY, fontsize=9)
        ax.set_title(
            f"{self.ticker}  Closing Prices  ({period})",
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

        self.status_lbl.configure(text=f"{n} trading days  •  last close ${prices[-1]:,.2f}")


# ── Main app ──────────────────────────────────────────────────────────────────

class StockApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Stock Price Viewer")
        self.geometry("1180x600")
        self.minsize(900, 440)
        self.tickers: list[str] = []
        self.rows:    dict[str, dict] = {}
        self._mover_rows: list[dict] = []
        self._build_ui()
        for t in DEFAULT_TICKERS:
            self._add_row(t)
        self.refresh()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── top bar ──
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            top_bar, text="Stock Price Viewer",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")

        # ── add ticker row ──
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.pack(fill="x", padx=16, pady=4)

        self.ticker_entry = ctk.CTkEntry(
            add_frame, placeholder_text="Ticker symbol (e.g. NVDA)", width=230,
        )
        self.ticker_entry.pack(side="left", padx=(0, 8))
        self.ticker_entry.bind("<Return>", lambda _: self._add_ticker())
        ctk.CTkButton(add_frame, text="Add", width=80, command=self._add_ticker).pack(side="left")

        # ── horizontal content area ──
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=4)

        self._build_watchlist(content)
        self._build_movers_panel(content)

        # ── bottom bar ──
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
            ("% Change", 110), ("Volume", 120), ("", 180),
        ]:
            ctk.CTkLabel(
                hdr, text=text, width=width, anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left", padx=8, pady=6)

        self.list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True)

    def _build_movers_panel(self, parent):
        right = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=10, width=310)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ctk.CTkLabel(
            right, text="Top Movers by Volume",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=12, pady=(12, 4), anchor="w")

        hdr = ctk.CTkFrame(right, fg_color=BG_HEADER, corner_radius=4)
        hdr.pack(fill="x", padx=8, pady=(0, 4))
        for text, width in [("#", 28), ("Symbol", 70), ("Volume", 100), ("% Chg", 78)]:
            ctk.CTkLabel(
                hdr, text=text, width=width, anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(side="left", padx=4, pady=4)

        # Pre-create TOP_N rows so we update labels instead of rebuilding
        rows_frame = ctk.CTkFrame(right, fg_color="transparent")
        rows_frame.pack(fill="both", expand=True, padx=8)

        for i in range(TOP_N):
            row = ctk.CTkFrame(rows_frame, fg_color=BG_ROW, corner_radius=4)
            row.pack(fill="x", pady=2)

            rank_lbl   = ctk.CTkLabel(row, text="—", width=28,  anchor="w", font=ctk.CTkFont(size=11))
            sym_lbl    = ctk.CTkLabel(row, text="—", width=70,  anchor="w", font=ctk.CTkFont(size=11, weight="bold"))
            vol_lbl    = ctk.CTkLabel(row, text="—", width=100, anchor="w", font=ctk.CTkFont(size=11))
            pct_lbl    = ctk.CTkLabel(row, text="—", width=78,  anchor="w", font=ctk.CTkFont(size=11))

            for lbl in (rank_lbl, sym_lbl, vol_lbl, pct_lbl):
                lbl.pack(side="left", padx=4, pady=5)

            self._mover_rows.append({
                "rank": rank_lbl, "symbol": sym_lbl,
                "volume": vol_lbl, "pct": pct_lbl,
            })

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
            ("symbol", 110, ticker),
            ("price",  120, "—"),
            ("change", 110, "—"),
            ("pct",    110, "—"),
            ("volume", 120, "—"),
        ]:
            font = ctk.CTkFont(weight="bold") if key == "symbol" else ctk.CTkFont()
            lbl  = ctk.CTkLabel(row, text=initial, width=width, anchor="w", font=font)
            lbl.pack(side="left", padx=8, pady=8)
            lbls[key] = lbl

        ctk.CTkButton(
            row, text="History", width=75,
            command=lambda t=ticker: self._open_history(t),
        ).pack(side="left", padx=(4, 2))

        ctk.CTkButton(
            row, text="Remove", width=75,
            fg_color="#922b21", hover_color="#6e1f18",
            command=lambda t=ticker: self._remove_ticker(t),
        ).pack(side="left", padx=(2, 4))

        self.rows[ticker] = {"frame": row, "labels": lbls}

    def _remove_ticker(self, ticker: str):
        if ticker in self.rows:
            self.rows[ticker]["frame"].destroy()
            del self.rows[ticker]
        if ticker in self.tickers:
            self.tickers.remove(ticker)

    def _open_history(self, ticker: str):
        win = HistoryWindow(self, ticker)
        win.focus()

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

    # ── Watchlist fetching ────────────────────────────────────────────────────

    def _fetch_all(self):
        tickers = list(self.tickers)
        threads = [threading.Thread(target=self._fetch_ticker, args=(t,), daemon=True) for t in tickers]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.after(0, self._done_refreshing)

    def _fetch_ticker(self, ticker: str):
        try:
            hist    = yf.Ticker(ticker).history(period="5d")
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

    # ── Movers fetching ───────────────────────────────────────────────────────

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

    def _update_movers(self, top: list[dict]):
        for i, row_lbls in enumerate(self._mover_rows):
            if i < len(top):
                entry = top[i]
                vol_m = entry["volume"] / 1_000_000
                pct   = entry["pct"]
                color = GREEN if pct >= 0 else RED
                sign  = "+" if pct >= 0 else ""
                row_lbls["rank"].configure(text=f"#{i + 1}")
                row_lbls["symbol"].configure(text=entry["ticker"])
                row_lbls["volume"].configure(text=f"{vol_m:.1f}M")
                row_lbls["pct"].configure(text=f"{sign}{pct:.2f}%", text_color=color)
            else:
                for key in ("rank", "symbol", "volume", "pct"):
                    row_lbls[key].configure(text="—", text_color="white")

        now = datetime.now().strftime("%I:%M %p")
        self.movers_status.configure(text=f"Updated {now}")

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
