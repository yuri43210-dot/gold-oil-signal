import os
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SYMBOLS = {
    "gold": {"label": "금", "symbol": "GC=F"},
    "oil": {"label": "원유", "symbol": "CL=F"},
    "silver": {"label": "은", "symbol": "SI=F"},
    "dxy": {"label": "달러지수", "symbol": "DX-Y.NYB"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_chart(symbol: str, interval: str = "5m", range_: str = "1d"):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": interval,
            "range": range_
        }
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        return result[0]
    except Exception as e:
        print(f"fetch_chart error for {symbol}: {e}")
        return None


def clean_close_series(chart_result):
    try:
        quote = chart_result.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", [])
        cleaned = [float(v) for v in closes if v is not None]
        return cleaned
    except Exception:
        return []


def pct_change(current, previous):
    if current is None or previous in (None, 0):
        return None
    return round(((current - previous) / previous) * 100, 2)


def build_sparkline_points(values, width=220, height=56, padding=6):
    if not values or len(values) < 2:
        return ""

    min_v = min(values)
    max_v = max(values)
    spread = max_v - min_v
    if spread == 0:
        spread = 1

    step_x = (width - padding * 2) / (len(values) - 1)

    points = []
    for i, value in enumerate(values):
        x = padding + i * step_x
        y = height - padding - ((value - min_v) / spread) * (height - padding * 2)
        points.append(f"{round(x, 2)},{round(y, 2)}")
    return " ".join(points)


def classify_signal(change_pct_value):
    if change_pct_value is None:
        return {
            "signal": "데이터 없음",
            "badge": "neutral",
        }
    if change_pct_value >= 0.5:
        return {
            "signal": "상승 우세",
            "badge": "bull",
        }
    if change_pct_value <= -0.5:
        return {
            "signal": "하락 우세",
            "badge": "bear",
        }
    return {
        "signal": "중립",
        "badge": "neutral",
    }


def auto_analysis(name, price, previous_close, change_pct_value, recent_trend):
    if price is None or previous_close is None:
        return f"{name} 데이터가 충분하지 않아 자동 분석을 제공할 수 없습니다."

    direction_text = "상승" if (change_pct_value or 0) > 0 else "하락" if (change_pct_value or 0) < 0 else "보합"

    if recent_trend == "up":
        trend_text = "최근 구간 차트도 우상향 흐름을 보여 단기 모멘텀이 유지되고 있습니다."
    elif recent_trend == "down":
        trend_text = "최근 구간 차트가 우하향 흐름이라 단기 압력이 이어질 수 있습니다."
    else:
        trend_text = "최근 구간 차트는 뚜렷한 방향성 없이 횡보 흐름입니다."

    if change_pct_value is None:
        return f"{name} 변동률을 계산하지 못했습니다. {trend_text}"

    return (
        f"현재 {name} 가격은 {round(price, 2)}이며 전일 종가 대비 {change_pct_value}% {direction_text}했습니다. "
        f"{trend_text}"
    )


def get_recent_trend(values):
    if len(values) < 6:
        return "flat"
    first = values[-6]
    last = values[-1]
    if last > first:
        return "up"
    if last < first:
        return "down"
    return "flat"


def build_item(name: str, symbol: str):
    chart = fetch_chart(symbol)
    if not chart:
        return {
            "name": name,
            "symbol": symbol,
            "price": None,
            "previous_close": None,
            "currency": None,
            "change_pct": None,
            "signal": "데이터 없음",
            "badge": "neutral",
            "analysis": f"{name} 가격 정보를 불러오지 못했습니다.",
            "sparkline": "",
        }

    meta = chart.get("meta", {})
    closes = clean_close_series(chart)
    last_24 = closes[-24:] if len(closes) >= 24 else closes

    price = meta.get("regularMarketPrice")
    previous_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    currency = meta.get("currency")
    change_pct_value = pct_change(price, previous_close)
    signal_info = classify_signal(change_pct_value)
    recent_trend = get_recent_trend(last_24)
    analysis = auto_analysis(name, price, previous_close, change_pct_value, recent_trend)
    sparkline = build_sparkline_points(last_24)

    return {
        "name": name,
        "symbol": symbol,
        "price": round(price, 2) if price is not None else None,
        "previous_close": round(previous_close, 2) if previous_close is not None else None,
        "currency": currency,
        "change_pct": change_pct_value,
        "analysis": analysis,
        "sparkline": sparkline,
        **signal_info,
    }


@app.route("/")
def index():
    return render_template("signal-page.html")


@app.route("/widget")
def widget():
    return render_template("mini-widget.html")


@app.route("/api/signals")
def signals():
    return jsonify({
        key: build_item(item["label"], item["symbol"])
        for key, item in SYMBOLS.items()
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
