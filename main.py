# -*- coding: utf-8 -*-
"""
StockDeskPro APK 手機完整版核心版
版本：2026-04-29

保留：
1. 強勢排行：代號、股票名稱、進場燈號、買點與停利區
2. 持股監控：代號與股票名稱、成本、股數、現價、持股燈號、買賣點判斷區、出場價
3. 決策助理：自動抓資料判斷 + 手動計算

刪除：
市場總攬、技術分析、新聞情緒、風險試算、交易日誌、AI分析、警示中心、
回測統計、第四階段、優化設定、設定頁、主力監控、主力強度、風險、AI總結

重點：
- 真正紅黃綠燈號色塊
- 不自動亂刷新，避免卡頓與跳動
- 所有按鈕防閃退
- 關閉/切頁/新增刪除時自動存檔
- 決策助理欄位標題固定顯示，不會因自動抓資料消失
"""

import os
import json
import time
import threading
from datetime import date, timedelta

try:
    import requests
except Exception:
    requests = None

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.properties import ListProperty


APP_NAME = "StockDeskPro"
FONT_FILE = "NotoSansTC-VariableFont_wght.ttf"

DEFAULT_FONT = "Roboto"
if os.path.exists(FONT_FILE):
    try:
        LabelBase.register(name="NotoTC", fn_regular=FONT_FILE)
        DEFAULT_FONT = "NotoTC"
    except Exception:
        DEFAULT_FONT = "Roboto"


SYMBOL_NAME_MAP = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2455.TW": "全新",
    "2303.TW": "聯電", "2382.TW": "廣達", "3034.TW": "聯詠", "2308.TW": "台達電",
    "2357.TW": "華碩", "3231.TW": "緯創", "6669.TW": "緯穎", "3661.TW": "世芯-KY",
    "3017.TW": "奇鋐", "3324.TW": "雙鴻", "3443.TW": "創意", "2376.TW": "技嘉",
    "2356.TW": "英業達", "4938.TW": "和碩", "2408.TW": "南亞科", "3008.TW": "大立光",
    "2603.TW": "長榮", "2609.TW": "陽明", "2615.TW": "萬海",
    "2881.TW": "富邦金", "2882.TW": "國泰金", "2891.TW": "中信金",
    "2886.TW": "兆豐金", "2884.TW": "玉山金", "2892.TW": "第一金",
    "0050.TW": "元大台灣50", "00830.TW": "國泰費城半導體",
    "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息",
    "00919.TW": "群益台灣精選高息", "00929.TW": "復華台灣科技優息",
    "00940.TW": "元大台灣價值高息",
}

DEFAULT_POOL = [
    "2330.TW", "2317.TW", "2454.TW", "2455.TW", "2303.TW",
    "2382.TW", "3034.TW", "2308.TW", "3231.TW", "6669.TW",
    "3017.TW", "3324.TW", "3443.TW", "2408.TW",
    "0050.TW", "00830.TW", "0056.TW", "00878.TW", "00919.TW"
]

DEFAULT_PORTFOLIO = [
    {"symbol": "0050.TW", "cost": 72.90, "shares": 13000, "manual_price": 0},
    {"symbol": "00830.TW", "cost": 56.15, "shares": 5000, "manual_price": 0},
    {"symbol": "2317.TW", "cost": 198.16, "shares": 3000, "manual_price": 0},
    {"symbol": "2408.TW", "cost": 215.00, "shares": 1000, "manual_price": 0},
    {"symbol": "2455.TW", "cost": 311.50, "shares": 1000, "manual_price": 0},
    {"symbol": "3231.TW", "cost": 139.00, "shares": 1000, "manual_price": 0},
]


# =========================
# 工具函式
# =========================
def normalize_symbol(symbol):
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return ""
    if "." not in symbol:
        return symbol + ".TW"
    return symbol


def stock_id(symbol):
    return normalize_symbol(symbol).replace(".TW", "").replace(".TWO", "")


def get_name(symbol):
    symbol = normalize_symbol(symbol)
    if not symbol or symbol == "手動":
        return ""
    return SYMBOL_NAME_MAP.get(symbol, symbol.replace(".TW", ""))


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").replace("%", "").strip()
        if text in ("", "--", "None", "nan"):
            return default
        return float(text)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return default


def fmt_num(value, digits=2):
    try:
        n = float(value)
        s = f"{n:,.{digits}f}"
        return s.rstrip("0").rstrip(".") if "." in s else s
    except Exception:
        return "--"


def pct_text(value):
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return "+0.00%"


def today_str():
    return date.today().strftime("%Y-%m-%d")


def start_date_str(days=300):
    return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")


def data_file_path():
    app = App.get_running_app()
    root = app.user_data_dir if app else os.getcwd()
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "stockdeskpro_mobile_data.json")


def default_data():
    return {
        "portfolio": [dict(x) for x in DEFAULT_PORTFOLIO],
        "pool": "\n".join(DEFAULT_POOL),
        "last_manual_quotes": {},
        "rank_limit": 12,
        "finmind_token": "",
    }


def load_data():
    base = default_data()
    path = data_file_path()
    try:
        if not os.path.exists(path):
            save_data(base)
            return base
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return base
        for k, v in base.items():
            data.setdefault(k, v)
        if not isinstance(data.get("portfolio"), list):
            data["portfolio"] = base["portfolio"]
        if not isinstance(data.get("last_manual_quotes"), dict):
            data["last_manual_quotes"] = {}
        return data
    except Exception:
        return base


def save_data(data):
    try:
        path = data_file_path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            with open(data_file_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


# =========================
# UI 元件
# =========================
class ColorBox(BoxLayout):
    bg_color = ListProperty([0.10, 0.12, 0.16, 1])

    def __init__(self, bg=(0.10, 0.12, 0.16, 1), radius=14, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = list(bg)
        self.radius = radius
        self.padding = kwargs.get("padding", dp(10))
        self.spacing = kwargs.get("spacing", dp(6))
        with self.canvas.before:
            self._color = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self.radius)])
        self.bind(pos=self._update_rect, size=self._update_rect, bg_color=self._update_color)

    def _update_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _update_color(self, *_):
        self._color.rgba = self.bg_color


class CLabel(Label):
    def __init__(self, text="", size=15, color=(0.92, 0.94, 0.98, 1), **kwargs):
        super().__init__(
            text=text,
            font_name=DEFAULT_FONT,
            font_size=dp(size),
            color=color,
            markup=True,
            halign=kwargs.pop("halign", "left"),
            valign=kwargs.pop("valign", "middle"),
            **kwargs
        )
        self.bind(size=self._sync_text_size)

    def _sync_text_size(self, *_):
        self.text_size = (self.width, None)


class CButton(Button):
    def __init__(self, text="", bg=(0.12, 0.32, 0.85, 1), **kwargs):
        super().__init__(
            text=text,
            font_name=DEFAULT_FONT,
            font_size=dp(15),
            background_normal="",
            background_down="",
            background_color=bg,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46),
            **kwargs
        )


class CInput(TextInput):
    def __init__(self, hint="", text="", multiline=False, **kwargs):
        super().__init__(
            hint_text=hint,
            text=str(text) if text is not None else "",
            font_name=DEFAULT_FONT,
            font_size=dp(15),
            multiline=multiline,
            background_color=(0.09, 0.11, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.60, 0.65, 0.74, 1),
            cursor_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(46) if not multiline else dp(130),
            padding=[dp(10), dp(10), dp(10), dp(10)],
            **kwargs
        )


class LabeledInput(BoxLayout):
    """固定標題 + 輸入框，標題不會因為輸入數值而消失。"""
    def __init__(self, title, hint="", **kwargs):
        # 防止外部呼叫時重複傳入高度相關參數
        kwargs.pop("size_hint_y", None)
        kwargs.pop("height", None)
        super().__init__(
            orientation="vertical",
            spacing=dp(3),
            size_hint_y=None,
            height=dp(70)
        )
        self.title_label = CLabel(
            title,
            size=12,
            color=(0.72, 0.77, 0.84, 1),
            size_hint_y=None,
            height=dp(18)
        )
        self.input = CInput(hint or title)
        self.add_widget(self.title_label)
        self.add_widget(self.input)

    @property
    def text(self):
        return self.input.text

    @text.setter
    def text(self, value):
        self.input.text = str(value) if value is not None else ""


class LightBadge(BoxLayout):
    def __init__(self, level="yellow", text="黃燈 觀察", **kwargs):
        # 防止外部呼叫時又傳 size_hint_y / height 造成 Kivy 重複參數閃退
        kwargs.pop("size_hint_y", None)
        kwargs.pop("height", None)
        super().__init__(orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(34), **kwargs)
        colors = {
            "green": (0.05, 0.68, 0.25, 1),
            "yellow": (0.95, 0.62, 0.05, 1),
            "red": (0.88, 0.12, 0.12, 1),
            "gray": (0.38, 0.42, 0.48, 1),
        }
        dot_wrap = BoxLayout(size_hint=(None, None), size=(dp(22), dp(30)), padding=(0, dp(6), 0, dp(6)))
        dot_wrap.add_widget(ColorBox(
            bg=colors.get(level, colors["yellow"]),
            radius=9,
            size_hint=(None, None),
            size=(dp(18), dp(18)),
            padding=0
        ))
        self.add_widget(dot_wrap)
        self.add_widget(CLabel(f"[b]{text}[/b]", size=14, size_hint_y=None, height=dp(30)))


class RowCard(ColorBox):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            bg=(0.075, 0.09, 0.12, 1),
            radius=16,
            padding=dp(12),
            spacing=dp(8),
            size_hint_y=None,
            **kwargs
        )
        self.bind(minimum_height=self.setter("height"))


# =========================
# 股票分析核心
# =========================
class Analyzer:
    URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, data):
        self.data = data
        self.cache = {}
        self.lock = threading.Lock()

    def headers(self):
        token = (self.data.get("finmind_token") or "").strip()
        return {"Authorization": f"Bearer {token}"} if token else {}

    def fetch_history(self, symbol):
        symbol = normalize_symbol(symbol)
        now = time.time()

        with self.lock:
            cached = self.cache.get(symbol)
            if cached and now - cached["time"] < 60 * 60 * 4:
                return cached["rows"]

        if requests is None:
            return []

        try:
            params = {
                "dataset": "TaiwanStockPrice",
                "data_id": stock_id(symbol),
                "start_date": start_date_str(),
                "end_date": today_str(),
            }
            resp = requests.get(self.URL, params=params, headers=self.headers(), timeout=8)
            data = resp.json()
            rows = data.get("data", []) if isinstance(data, dict) else []
            rows = sorted(rows, key=lambda x: x.get("date", ""))

            with self.lock:
                self.cache[symbol] = {"time": now, "rows": rows}
            return rows
        except Exception:
            return []

    def indicators(self, symbol):
        rows = self.fetch_history(symbol)

        closes, highs, lows, vols = [], [], [], []
        for row in rows:
            close = safe_float(row.get("close"))
            if close > 0:
                closes.append(close)
                highs.append(safe_float(row.get("max"), close))
                lows.append(safe_float(row.get("min"), close))
                vols.append(safe_float(row.get("Trading_Volume"), 0))

        if len(closes) < 30:
            return {
                "ma5": 0,
                "ma10": 0,
                "ma20": 0,
                "ma60": 0,
                "prev_high": 0,
                "prev_low": 0,
                "vol_ratio": 0,
            }

        def ma(n):
            return sum(closes[-n:]) / n if len(closes) >= n else 0

        vol20 = sum(vols[-20:]) / 20 if len(vols) >= 20 else 0
        last_vol = vols[-1] if vols else 0

        return {
            "ma5": ma(5),
            "ma10": ma(10),
            "ma20": ma(20),
            "ma60": ma(60) if len(closes) >= 60 else 0,
            "prev_high": max(highs[-21:-1]) if len(highs) >= 21 else max(highs),
            "prev_low": min(lows[-21:-1]) if len(lows) >= 21 else min(lows),
            "vol_ratio": last_vol / vol20 if vol20 else 0,
        }

    def quote(self, symbol):
        symbol = normalize_symbol(symbol)
        manual = safe_float(self.data.get("last_manual_quotes", {}).get(symbol), 0)
        rows = self.fetch_history(symbol)

        if len(rows) >= 2:
            last = rows[-1]
            prev = rows[-2]
            price = manual if manual > 0 else safe_float(last.get("close"))
            prev_close = safe_float(prev.get("close"))
            pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            return {"symbol": symbol, "name": get_name(symbol), "price": price, "pct": pct}

        if manual > 0:
            return {"symbol": symbol, "name": get_name(symbol), "price": manual, "pct": 0}

        return {"symbol": symbol, "name": get_name(symbol), "price": 0, "pct": 0}

    def decision(self, price, ma5, ma10, ma20, prev_high, vol_ratio, pct=0):
        price = safe_float(price)
        ma5 = safe_float(ma5)
        ma10 = safe_float(ma10)
        ma20 = safe_float(ma20)
        prev_high = safe_float(prev_high)
        vol_ratio = safe_float(vol_ratio)
        pct = safe_float(pct)

        if price <= 0:
            return {
                "level": "gray",
                "light": "灰燈 無資料",
                "score": 0,
                "buy_zone": "等待有效價格",
                "take_profit": "等待資料",
                "exit_price": "自行設定",
                "position": "0%",
                "notes": "目前沒有有效價格資料",
            }

        score = 50
        notes = []
        warnings = []

        trend_ok = ma5 > 0 and ma10 > 0 and ma20 > 0 and ma5 >= ma10 >= ma20
        pullback_buy = trend_ok and price >= ma10 * 0.985 and price <= ma5 * 1.035
        breakout_buy = prev_high > 0 and price > prev_high and vol_ratio >= 1.3 and pct < 5
        near_breakout = prev_high > 0 and price >= prev_high * 0.985 and not breakout_buy
        weak = (ma20 > 0 and price < ma20) or (ma10 > 0 and price < ma10 * 0.97)

        if trend_ok:
            score += 16
            notes.append("均線偏多")
        if pullback_buy:
            score += 18
            notes.append("接近5日/10日買點")
        if breakout_buy:
            score += 22
            notes.append("突破有量")
        elif near_breakout:
            score -= 6
            notes.append("接近前高，等確認")

        if vol_ratio >= 2:
            score += 12
            notes.append("量能強")
        elif vol_ratio >= 1.3:
            score += 6
            notes.append("量能放大")
        elif near_breakout:
            score -= 12
            warnings.append("突破量不足")

        if pct >= 5:
            score -= 20
            warnings.append("大漲後避免追高")
        elif pct >= 3:
            score -= 8
            warnings.append("偏追高，等拉回")

        if ma5 > 0 and (price - ma5) / ma5 * 100 > 5:
            score -= 16
            warnings.append("離5日線太遠")
        if weak:
            score -= 28
            warnings.append("跌破關鍵均線")

        score = max(0, min(100, round(score)))

        if weak or score < 55:
            level, light, position = "red", "紅燈 不進場", "0%"
        elif score < 78:
            level, light, position = "yellow", "黃燈 等拉回", "0%~10%"
        else:
            level, light, position = "green", "綠燈 可試單", "10%~30%"

        if breakout_buy and prev_high > 0:
            buy_zone = f"{fmt_num(prev_high)} 回測不破"
            stop_price = max(prev_high * 0.985, ma5 if ma5 > 0 else price * 0.96)
        elif ma5 > 0 and ma10 > 0:
            buy_zone = f"{fmt_num(ma5)} ~ {fmt_num(ma10)}"
            stop_price = ma10 * 0.985
        elif ma20 > 0:
            buy_zone = f"{fmt_num(ma20)} 附近"
            stop_price = ma20 * 0.985
        else:
            buy_zone = "等型態確認"
            stop_price = price * 0.94

        risk = max(price - stop_price, price * 0.01)
        take_profit1 = price + risk * 1.5
        take_profit2 = price + risk * 2.5

        reason = notes + warnings
        if not reason:
            reason = ["中性觀察"]

        return {
            "level": level,
            "light": light,
            "score": score,
            "buy_zone": buy_zone,
            "take_profit": f"{fmt_num(take_profit1)} / {fmt_num(take_profit2)}",
            "exit_price": fmt_num(stop_price),
            "position": position,
            "notes": " / ".join(reason),
        }

    def analyze(self, symbol):
        quote = self.quote(symbol)
        ind = self.indicators(symbol)
        dec = self.decision(
            quote.get("price", 0),
            ind.get("ma5", 0),
            ind.get("ma10", 0),
            ind.get("ma20", 0),
            ind.get("prev_high", 0),
            ind.get("vol_ratio", 0),
            quote.get("pct", 0),
        )
        return {**quote, **ind, **dec}

    def rank(self):
        symbols = [normalize_symbol(x) for x in self.data.get("pool", "").splitlines() if normalize_symbol(x)]
        rows = []
        for symbol in symbols[:30]:
            item = self.analyze(symbol)
            item["rank_score"] = (
                safe_float(item.get("score"))
                + min(max(safe_float(item.get("pct")), -5), 8) * 2
                + min(safe_float(item.get("vol_ratio")), 3) * 4
            )
            rows.append(item)

        rows.sort(key=lambda x: x.get("rank_score", 0), reverse=True)
        return rows[:safe_int(self.data.get("rank_limit"), 12)]


# =========================
# 頁面
# =========================
class BaseScreen(Screen):
    def header(self, text):
        box = ColorBox(
            orientation="vertical",
            bg=(0.06, 0.08, 0.11, 1),
            radius=0,
            padding=dp(10),
            size_hint_y=None,
            height=dp(54)
        )
        box.add_widget(CLabel(f"[b]{text}[/b]", size=20, halign="center"))
        return box

    def status(self, content, text):
        content.clear_widgets()
        card = RowCard()
        card.add_widget(CLabel(text, size=15, size_hint_y=None, height=dp(42)))
        content.add_widget(card)


class RankScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        root.add_widget(self.header("強勢排行"))

        top = BoxLayout(size_hint_y=None, height=dp(54), padding=dp(8))
        refresh_btn = CButton("重新整理", bg=(0.10, 0.34, 0.78, 1))
        refresh_btn.bind(on_press=lambda *_: self.refresh())
        top.add_widget(refresh_btn)
        root.add_widget(top)

        scroll = ScrollView(do_scroll_x=False)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(8))
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        root.add_widget(scroll)

    def on_pre_enter(self):
        if not self.content.children:
            self.refresh()

    def refresh(self):
        self.status(self.content, "排行讀取中...")
        app = App.get_running_app()

        def worker():
            try:
                rows = app.analyzer.rank()
                Clock.schedule_once(lambda dt: self.show_rows(rows), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.status(self.content, f"排行錯誤：{e}"), 0)

        threading.Thread(target=worker, daemon=True).start()

    def show_rows(self, rows):
        self.content.clear_widgets()

        if not rows:
            self.status(self.content, "沒有資料，請檢查網路。")
            return

        for item in rows:
            card = RowCard()

            top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(38), spacing=dp(8))
            top.add_widget(CLabel(f"[b]{item.get('symbol', '')}[/b]  {item.get('name', '')}", size=17))
            top.add_widget(LightBadge(
                item.get("level", "yellow"),
                item.get("light", "黃燈 觀察"),
                size_hint_x=None,
                width=dp(138)
            ))
            card.add_widget(top)

            card.add_widget(CLabel(f"買點：{item.get('buy_zone', '--')}", size=15, size_hint_y=None, height=dp(28)))
            card.add_widget(CLabel(f"停利區：{item.get('take_profit', '--')}", size=15, size_hint_y=None, height=dp(28)))
            card.add_widget(CLabel(
                f"現價 {fmt_num(item.get('price'))}｜漲跌 {pct_text(item.get('pct'))}｜分數 {item.get('score')}",
                size=12,
                color=(0.68, 0.73, 0.80, 1),
                size_hint_y=None,
                height=dp(24)
            ))
            self.content.add_widget(card)


class PortfolioScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical")
        self.add_widget(root)
        root.add_widget(self.header("持股監控"))

        form = ColorBox(
            orientation="vertical",
            bg=(0.065, 0.08, 0.11, 1),
            radius=0,
            padding=dp(8),
            spacing=dp(6),
            size_hint_y=None,
            height=dp(160)
        )

        row1 = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(44))
        self.symbol_input = CInput("代號，例如 2330")
        self.cost_input = CInput("成本")
        row1.add_widget(self.symbol_input)
        row1.add_widget(self.cost_input)

        row2 = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(44))
        self.shares_input = CInput("股數")
        self.price_input = CInput("手動現價，可空白")
        row2.add_widget(self.shares_input)
        row2.add_widget(self.price_input)

        row3 = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(44))
        add_btn = CButton("新增持股", bg=(0.10, 0.34, 0.78, 1))
        add_btn.bind(on_press=lambda *_: self.add_holding())
        refresh_btn = CButton("重新整理", bg=(0.12, 0.48, 0.28, 1))
        refresh_btn.bind(on_press=lambda *_: self.refresh())
        row3.add_widget(add_btn)
        row3.add_widget(refresh_btn)

        form.add_widget(row1)
        form.add_widget(row2)
        form.add_widget(row3)
        root.add_widget(form)

        self.summary = CLabel("", size=15, halign="center", size_hint_y=None, height=dp(36))
        root.add_widget(self.summary)

        scroll = ScrollView(do_scroll_x=False)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(8))
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        root.add_widget(scroll)

    def on_pre_enter(self):
        if not self.content.children:
            self.refresh()

    def add_holding(self):
        app = App.get_running_app()

        symbol = normalize_symbol(self.symbol_input.text)
        cost = safe_float(self.cost_input.text)
        shares = safe_int(self.shares_input.text)
        manual_price = safe_float(self.price_input.text)

        if not symbol or cost <= 0 or shares <= 0:
            self.summary.text = "請輸入正確代號、成本、股數"
            return

        app.data.setdefault("portfolio", []).append({
            "symbol": symbol,
            "cost": cost,
            "shares": shares,
            "manual_price": manual_price
        })

        if manual_price > 0:
            app.data.setdefault("last_manual_quotes", {})[symbol] = manual_price

        app.save_now()

        self.symbol_input.text = ""
        self.cost_input.text = ""
        self.shares_input.text = ""
        self.price_input.text = ""

        self.refresh()

    def delete_holding(self, idx):
        app = App.get_running_app()
        try:
            app.data["portfolio"].pop(idx)
            app.save_now()
            self.refresh()
        except Exception:
            pass

    def refresh(self):
        self.status(self.content, "持股讀取中...")
        app = App.get_running_app()

        def worker():
            rows = []
            total_cost = 0
            total_value = 0

            try:
                for idx, holding in enumerate(app.data.get("portfolio", [])):
                    symbol = normalize_symbol(holding.get("symbol"))
                    cost = safe_float(holding.get("cost"))
                    shares = safe_int(holding.get("shares"))
                    manual_price = safe_float(holding.get("manual_price"))

                    if manual_price > 0:
                        app.data.setdefault("last_manual_quotes", {})[symbol] = manual_price

                    item = app.analyzer.analyze(symbol)
                    price = safe_float(item.get("price"), manual_price if manual_price > 0 else cost)

                    total_cost += cost * shares
                    total_value += price * shares
                    rows.append((idx, holding, item, price))

                Clock.schedule_once(lambda dt: self.show_rows(rows, total_cost, total_value), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.status(self.content, f"持股錯誤：{e}"), 0)

        threading.Thread(target=worker, daemon=True).start()

    def show_rows(self, rows, total_cost, total_value):
        self.content.clear_widgets()

        pnl = total_value - total_cost
        pnl_pct = pnl / total_cost * 100 if total_cost else 0
        self.summary.text = f"總損益：{fmt_num(pnl)}（{pct_text(pnl_pct)}）"

        if not rows:
            self.status(self.content, "目前沒有持股。")
            return

        for idx, holding, item, price in rows:
            cost = safe_float(holding.get("cost"))
            shares = safe_int(holding.get("shares"))
            pnl = (price - cost) * shares
            pnl_pct = (price - cost) / cost * 100 if cost else 0

            if pnl_pct <= -8:
                level, light = "red", "紅燈 檢查出場"
            elif pnl_pct >= 12:
                level, light = "green", "綠燈 續抱/分批停利"
            else:
                level = item.get("level", "yellow")
                if level == "green":
                    light = "綠燈 偏強續抱"
                elif level == "red":
                    light = "紅燈 保守防守"
                else:
                    light = "黃燈 觀察"

            card = RowCard()

            top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(38), spacing=dp(8))
            top.add_widget(CLabel(f"[b]{holding.get('symbol')}[/b]  {get_name(holding.get('symbol'))}", size=17))
            top.add_widget(LightBadge(level, light, size_hint_x=None, width=dp(160)))
            card.add_widget(top)

            card.add_widget(CLabel(
                f"成本：{fmt_num(cost)}｜股數：{shares:,}｜現價：{fmt_num(price)}",
                size=15,
                size_hint_y=None,
                height=dp(28)
            ))
            card.add_widget(CLabel(
                f"損益：{fmt_num(pnl)}（{pct_text(pnl_pct)}）",
                size=15,
                size_hint_y=None,
                height=dp(28)
            ))
            card.add_widget(CLabel(
                f"買賣點判斷：{item.get('notes', '--')}",
                size=14,
                size_hint_y=None,
                height=dp(48)
            ))
            card.add_widget(CLabel(
                f"出場價：{item.get('exit_price', '--')}",
                size=15,
                size_hint_y=None,
                height=dp(28)
            ))

            delete_btn = CButton("刪除這筆", bg=(0.60, 0.12, 0.12, 1))
            delete_btn.bind(on_press=lambda _btn, i=idx: self.delete_holding(i))
            card.add_widget(delete_btn)

            self.content.add_widget(card)


class DecisionScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical")
        self.add_widget(root)
        root.add_widget(self.header("決策助理"))

        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(8))
        body.bind(minimum_height=body.setter("height"))
        scroll.add_widget(body)
        root.add_widget(scroll)

        form = ColorBox(
            orientation="vertical",
            bg=(0.065, 0.08, 0.11, 1),
            radius=16,
            padding=dp(10),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(450)
        )

        self.symbol_input = CInput("股票代號，例如 2330")
        form.add_widget(self.symbol_input)

        auto_btn = CButton("自動抓資料判斷", bg=(0.10, 0.34, 0.78, 1))
        auto_btn.bind(on_press=lambda *_: self.auto_decide())
        form.add_widget(auto_btn)

        row1 = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(70))
        self.price_input = LabeledInput("現價")
        self.ma5_input = LabeledInput("MA5")
        row1.add_widget(self.price_input)
        row1.add_widget(self.ma5_input)
        form.add_widget(row1)

        row2 = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(70))
        self.ma10_input = LabeledInput("MA10")
        self.ma20_input = LabeledInput("MA20")
        row2.add_widget(self.ma10_input)
        row2.add_widget(self.ma20_input)
        form.add_widget(row2)

        row3 = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(70))
        self.prev_high_input = LabeledInput("前高")
        self.vol_ratio_input = LabeledInput("量比")
        row3.add_widget(self.prev_high_input)
        row3.add_widget(self.vol_ratio_input)
        form.add_widget(row3)

        manual_btn = CButton("手動計算", bg=(0.12, 0.48, 0.28, 1))
        manual_btn.bind(on_press=lambda *_: self.manual_decide())
        form.add_widget(manual_btn)

        body.add_widget(form)

        self.result_box = ColorBox(
            orientation="vertical",
            bg=(0.075, 0.09, 0.12, 1),
            radius=16,
            padding=dp(12),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(270)
        )
        self.result_box.add_widget(CLabel("請輸入代號或手動數據後計算。", size=16, size_hint_y=None, height=dp(40)))
        body.add_widget(self.result_box)

    def show_message(self, text):
        self.result_box.clear_widgets()
        self.result_box.add_widget(CLabel(text, size=16, size_hint_y=None, height=dp(60)))

    def show_result(self, symbol, name, decision):
        self.result_box.clear_widgets()
        self.result_box.add_widget(CLabel(f"[b]{symbol} {name}[/b]", size=18, size_hint_y=None, height=dp(34)))
        self.result_box.add_widget(LightBadge(
            decision.get("level", "yellow"),
            decision.get("light", "黃燈 觀察"),
            size_hint_y=None,
            height=dp(38)
        ))
        self.result_box.add_widget(CLabel(f"買點：{decision.get('buy_zone', '--')}", size=15, size_hint_y=None, height=dp(30)))
        self.result_box.add_widget(CLabel(f"停利區：{decision.get('take_profit', '--')}", size=15, size_hint_y=None, height=dp(30)))
        self.result_box.add_widget(CLabel(f"出場價：{decision.get('exit_price', '--')}", size=15, size_hint_y=None, height=dp(30)))
        self.result_box.add_widget(CLabel(f"建議部位：{decision.get('position', '--')}", size=15, size_hint_y=None, height=dp(30)))
        self.result_box.add_widget(CLabel(
            f"理由：{decision.get('notes', '--')}",
            size=14,
            color=(0.72, 0.77, 0.84, 1)
        ))

    def auto_decide(self):
        app = App.get_running_app()
        symbol = normalize_symbol(self.symbol_input.text)

        if not symbol:
            self.show_message("請先輸入股票代號。")
            return

        self.show_message("資料讀取中...")

        def worker():
            try:
                item = app.analyzer.analyze(symbol)
                Clock.schedule_once(lambda dt: self.apply_auto_result(item), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_message(f"自動判斷錯誤：{e}"), 0)

        threading.Thread(target=worker, daemon=True).start()

    def apply_auto_result(self, item):
        try:
            self.price_input.text = fmt_num(item.get("price"))
            self.ma5_input.text = fmt_num(item.get("ma5"))
            self.ma10_input.text = fmt_num(item.get("ma10"))
            self.ma20_input.text = fmt_num(item.get("ma20"))
            self.prev_high_input.text = fmt_num(item.get("prev_high"))
            self.vol_ratio_input.text = fmt_num(item.get("vol_ratio"))

            self.show_result(item.get("symbol", ""), item.get("name", ""), item)

            app = App.get_running_app()
            symbol = item.get("symbol", "")
            price = safe_float(item.get("price"))
            if symbol and price > 0:
                app.data.setdefault("last_manual_quotes", {})[symbol] = price
                app.save_now()
        except Exception as e:
            self.show_message(f"顯示結果錯誤：{e}")

    def manual_decide(self):
        app = App.get_running_app()

        try:
            decision = app.analyzer.decision(
                self.price_input.text,
                self.ma5_input.text,
                self.ma10_input.text,
                self.ma20_input.text,
                self.prev_high_input.text,
                self.vol_ratio_input.text,
                0
            )

            symbol_text = self.symbol_input.text.strip()
            symbol = normalize_symbol(symbol_text) if symbol_text else "手動"

            if symbol != "手動" and safe_float(self.price_input.text) > 0:
                app.data.setdefault("last_manual_quotes", {})[symbol] = safe_float(self.price_input.text)
                app.save_now()

            self.show_result(symbol, get_name(symbol), decision)
        except Exception as e:
            self.show_message(f"手動計算錯誤：{e}")


class Root(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        with self.canvas.before:
            Color(0.045, 0.055, 0.075, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        top = ColorBox(
            orientation="vertical",
            bg=(0.045, 0.055, 0.075, 1),
            radius=0,
            padding=dp(8),
            size_hint_y=None,
            height=dp(50)
        )
        top.add_widget(CLabel(f"[b]{APP_NAME}[/b]", size=18, halign="center"))
        self.add_widget(top)

        self.manager = ScreenManager(transition=NoTransition())
        self.manager.add_widget(RankScreen(name="rank"))
        self.manager.add_widget(PortfolioScreen(name="portfolio"))
        self.manager.add_widget(DecisionScreen(name="decision"))
        self.add_widget(self.manager)

        nav = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(1))
        for text, screen in [
            ("強勢排行", "rank"),
            ("持股監控", "portfolio"),
            ("決策助理", "decision"),
        ]:
            btn = CButton(text, bg=(0.08, 0.12, 0.18, 1))
            btn.bind(on_press=lambda _btn, s=screen: self.switch(s))
            nav.add_widget(btn)
        self.add_widget(nav)

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def switch(self, screen):
        app = App.get_running_app()
        if app:
            app.save_now()
        self.manager.current = screen


class StockDeskApp(App):
    def build(self):
        self.title = APP_NAME
        Window.clearcolor = (0.045, 0.055, 0.075, 1)
        self.data = load_data()
        self.analyzer = Analyzer(self.data)
        return Root()

    def save_now(self):
        save_data(self.data)

    def on_pause(self):
        self.save_now()
        return True

    def on_stop(self):
        self.save_now()


if __name__ == "__main__":
    StockDeskApp().run()
