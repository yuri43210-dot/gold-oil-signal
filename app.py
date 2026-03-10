import os
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
