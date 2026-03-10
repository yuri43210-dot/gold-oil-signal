import os
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SYMBOLS = {
    "gold": "GC=F",
    "oil": "CL=F",
    "silver": "SI=F",
    "dxy": "DX-Y.NYB"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_chart_meta(symbol: str):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": "5m",
            "range": "1d"
        }
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        result = data.get("chart", {}).get("result", [])
        if not result:
            return None

        meta = result[0].get("meta", {})
        return meta
    except Exception as e:
        print(f"fetch_chart_meta error for {symbol}: {e}")
        return None


def classify_signal(price, previous_close):
    if price is None or previous_close in (None, 0):
        return {
            "signal": "데이터 없음",
            "badge": "neutral",
            "change_pct": None,
            "summary": "실시간 가격 데이터를 충분히 받지 못했습니다."
        }

    change_pct = round(((price - previous_close) / previous_close) * 100, 2)

    if change_pct >= 0.5:
        return {
            "signal": "상승 우세",
            "badge": "bull",
            "change_pct": change_pct,
            "summary": "전일 종가 대비 상승폭이 커 단기 강세 흐름입니다."
        }
    elif change_pct <= -0.5:
        return {
            "signal": "하락 우세",
            "badge": "bear",
            "change_pct": change_pct,
            "summary": "전일 종가 대비 하락폭이 커 단기 약세 흐름입니다."
        }
    else:
        return {
            "signal": "중립",
            "badge": "neutral",
            "change_pct": change_pct,
            "summary": "전일 종가 대비 변동폭이 크지 않아 관망 구간입니다."
        }


def build_item(name: str, symbol: str):
    meta = fetch_chart_meta(symbol)
    if not meta:
        return {
            "name": name,
            "symbol": symbol,
            "price": None,
            "previous_close": None,
            "signal": "데이터 없음",
            "badge": "neutral",
            "change_pct": None,
            "currency": None,
            "summary": "가격 정보를 불러오지 못했습니다."
        }

    price = meta.get("regularMarketPrice")
    previous_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    currency = meta.get("currency")

    signal_info = classify_signal(price, previous_close)

    return {
        "name": name,
        "symbol": symbol,
        "price": price,
        "previous_close": previous_close,
        "currency": currency,
        **signal_info
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
        "gold": build_item("금", SYMBOLS["gold"]),
        "oil": build_item("원유", SYMBOLS["oil"]),
        "silver": build_item("은", SYMBOLS["silver"]),
        "dxy": build_item("달러지수", SYMBOLS["dxy"])
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
