import os
import requests
from flask import Flask, jsonify, render_template, abort

app = Flask(__name__)

SYMBOLS = {
    "gold": {"label": "금", "symbol": "GC=F", "slug": "gold"},
    "oil": {"label": "원유", "symbol": "CL=F", "slug": "oil"},
    "silver": {"label": "은", "symbol": "SI=F", "slug": "silver"},
    "dxy": {"label": "달러지수", "symbol": "DX-Y.NYB", "slug": "dollar"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


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
        return [float(v) for v in closes if v is not None]
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
    spread = max_v - min_v or 1
    step_x = (width - padding * 2) / (len(values) - 1)

    points = []
    for i, value in enumerate(values):
        x = padding + i * step_x
        y = height - padding - ((value - min_v) / spread) * (height - padding * 2)
        points.append(f"{round(x, 2)},{round(y, 2)}")
    return " ".join(points)


def classify_signal(change_pct_value):
    if change_pct_value is None:
        return {"signal": "데이터 없음", "badge": "neutral"}
    if change_pct_value >= 0.5:
        return {"signal": "상승 우세", "badge": "bull"}
    if change_pct_value <= -0.5:
        return {"signal": "하락 우세", "badge": "bear"}
    return {"signal": "중립", "badge": "neutral"}


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


def auto_analysis(name, price, previous_close, change_pct_value, recent_trend):
    if price is None or previous_close is None or change_pct_value is None:
        return f"{name} 데이터가 충분하지 않아 자동 분석을 제공할 수 없습니다."

    direction_text = "상승" if change_pct_value > 0 else "하락" if change_pct_value < 0 else "보합"

    if recent_trend == "up":
        trend_text = "최근 구간 차트도 우상향 흐름을 보여 단기 모멘텀이 유지되고 있습니다."
    elif recent_trend == "down":
        trend_text = "최근 구간 차트가 우하향 흐름이라 단기 압력이 이어질 수 있습니다."
    else:
        trend_text = "최근 구간 차트는 뚜렷한 방향성 없이 횡보 흐름입니다."

    return (
        f"현재 {name} 가격은 {round(price, 2)}이며 전일 종가 대비 {change_pct_value}% {direction_text}했습니다. "
        f"{trend_text}"
    )


def get_cta(item_key, signal):
    if item_key == "gold":
        return {
            "title": "금 가격 전망과 투자 전략",
            "desc": "금 ETF, 금 채굴주, 인버스 전략 등 참고 아이디어를 확인할 수 있습니다.",
            "link": "/gold-forecast",
            "button": "금값 전망·전략 보기"
        }

    if item_key == "oil":
        return {
            "title": "국제유가 전망과 투자 전략",
            "desc": "에너지 ETF, 정유주, 운송·항공 업종 등 연결 자산을 함께 볼 수 있습니다.",
            "link": "/oil-forecast",
            "button": "국제유가 전망·전략 보기"
        }

    if item_key == "silver":
        return {
            "title": "은 가격 전략 페이지",
            "desc": "은 가격과 산업 수요를 함께 보는 전략 페이지입니다.",
            "link": "/silver-strategy",
            "button": "은 전략 보기"
        }

    return {
        "title": "달러지수 전략 페이지",
        "desc": "달러 강세·약세 흐름과 원자재 관계를 함께 볼 수 있습니다.",
        "link": "/dollar-strategy",
        "button": "달러 전략 보기"
    }


def get_asset_cta(item_key, signal):
    if item_key == "gold":
        if signal == "하락 우세":
            return {
                "title": "금 하락 시 참고 자산",
                "desc": "달러 강세 자산, 금 인버스 ETF, 방어형 전략을 볼 수 있습니다.",
                "link": "/gold-down-assets",
                "button": "금 하락 추천 자산 보기"
            }
        if signal == "상승 우세":
            return {
                "title": "금 상승 시 참고 자산",
                "desc": "금 ETF, 금 채굴주, 안전자산 확대 전략을 확인할 수 있습니다.",
                "link": "/gold-up-assets",
                "button": "금 상승 추천 자산 보기"
            }
        return {
            "title": "금 관망 구간 참고 자산",
            "desc": "횡보 구간 분산 전략과 관련 자산을 확인할 수 있습니다.",
            "link": "/gold-up-assets",
            "button": "금 관련 자산 보기"
        }

    if item_key == "oil":
        if signal == "상승 우세":
            return {
                "title": "유가 상승 시 수혜 자산",
                "desc": "에너지 ETF, 정유주, 탐사·생산 기업을 정리한 페이지입니다.",
                "link": "/oil-up-assets",
                "button": "유가 상승 추천 자산 보기"
            }
        if signal == "하락 우세":
            return {
                "title": "유가 하락 시 참고 자산",
                "desc": "항공, 운송, 원가 절감 수혜 업종을 정리한 페이지입니다.",
                "link": "/oil-down-assets",
                "button": "유가 하락 추천 자산 보기"
            }
        return {
            "title": "유가 관망 구간 참고 자산",
            "desc": "횡보 구간 관련 업종과 분산 전략을 정리했습니다.",
            "link": "/oil-up-assets",
            "button": "유가 관련 자산 보기"
        }

    if item_key == "silver":
        return {
            "title": "은 관련 참고 자산",
            "desc": "은 ETF, 귀금속 분산, 산업 수요 관련 관점을 정리했습니다.",
            "link": "/silver-assets",
            "button": "은 추천 자산 보기"
        }

    return {
        "title": "달러지수 관련 참고 자산",
        "desc": "달러 강세·약세 구간에서 함께 보는 자산 아이디어를 정리했습니다.",
        "link": "/dollar-assets",
        "button": "달러 추천 자산 보기"
    }


def build_item(item_key: str, name: str, symbol: str, slug: str):
    chart = fetch_chart(symbol)
    if not chart:
        signal = "데이터 없음"
        return {
            "name": name,
            "symbol": symbol,
            "slug": slug,
            "price": None,
            "previous_close": None,
            "currency": None,
            "change_pct": None,
            "signal": signal,
            "badge": "neutral",
            "analysis": f"{name} 가격 정보를 불러오지 못했습니다.",
            "sparkline": "",
            "cta": get_cta(item_key, signal),
            "asset_cta": get_asset_cta(item_key, signal),
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

    return {
        "name": name,
        "symbol": symbol,
        "slug": slug,
        "price": round(price, 2) if price is not None else None,
        "previous_close": round(previous_close, 2) if previous_close is not None else None,
        "currency": currency,
        "change_pct": change_pct_value,
        "analysis": analysis,
        "sparkline": build_sparkline_points(last_24),
        "cta": get_cta(item_key, signal_info["signal"]),
        "asset_cta": get_asset_cta(item_key, signal_info["signal"]),
        **signal_info,
    }


def all_items():
    return {
        key: build_item(key, item["label"], item["symbol"], item["slug"])
        for key, item in SYMBOLS.items()
    }


def forecast_context(item_key: str, title: str, intro: str, sections: list[str]):
    items = all_items()
    item = items[item_key]
    return {
        "title": title,
        "item": item,
        "intro": intro,
        "sections": sections,
        "all_items": items,
    }


def asset_page_context(item_key: str, title: str, intro: str, assets: list[dict]):
    items = all_items()
    item = items[item_key]
    return {
        "title": title,
        "item": item,
        "intro": intro,
        "assets": assets,
        "all_items": items,
    }


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/widget")
def widget():
    return render_template("widget.html")


@app.route("/embed/<asset_key>")
def embed_single(asset_key):
    items = all_items()
    if asset_key == "dollar":
        item = items["dxy"]
    elif asset_key in items:
        item = items[asset_key]
    else:
        abort(404)
    return render_template("embed_single.html", item=item)


@app.route("/api/signals")
def signals():
    return jsonify(all_items())


@app.route("/gold-forecast")
def gold_forecast():
    return render_template(
        "forecast.html",
        **forecast_context(
            "gold",
            "오늘 금값 전망 | 금 투자 전략 총정리",
            "금 가격 흐름과 차트를 바탕으로 오늘 금값 전망과 투자 전략 아이디어를 정리한 페이지입니다.",
            [
                "금 가격이 강세일 때는 금 ETF, 금 채굴주, 안전자산 선호 흐름이 함께 부각되는지 확인하는 경우가 많습니다.",
                "금 가격이 약세일 때는 달러 강세, 금리 흐름, 금 인버스 ETF 등 반대 방향 자산도 함께 비교하는 전략이 사용되기도 합니다.",
                "실제 투자 판단 전에는 금리, 달러지수, 지정학 이슈, 중앙은행 수요 등도 같이 확인하는 것이 좋습니다."
            ]
        )
    )


@app.route("/oil-forecast")
def oil_forecast():
    return render_template(
        "forecast.html",
        **forecast_context(
            "oil",
            "오늘 국제유가 전망 | 원유 투자 전략 총정리",
            "WTI 원유 가격 흐름을 기준으로 국제유가 전망과 관련 투자 전략 아이디어를 정리한 페이지입니다.",
            [
                "유가가 상승할 때는 에너지 ETF, 정유주, 탐사·생산 기업이 주목받는 경우가 있습니다.",
                "유가가 하락할 때는 항공, 운송, 원가 절감 수혜 업종을 함께 보는 전략도 있습니다.",
                "국제유가는 OPEC 정책, 재고 지표, 달러 흐름, 지정학 변수의 영향을 많이 받기 때문에 함께 확인하는 것이 좋습니다."
            ]
        )
    )


@app.route("/silver-strategy")
def silver_strategy():
    return render_template(
        "forecast.html",
        **forecast_context(
            "silver",
            "은 가격 전략 | 은 투자 아이디어 정리",
            "은 가격 흐름과 산업재·귀금속 특성을 함께 고려한 전략 아이디어 페이지입니다.",
            [
                "은은 금과 함께 안전자산 흐름을 받을 수 있지만 산업 수요 영향도 크기 때문에 더 큰 변동성을 보일 수 있습니다.",
                "태양광, 전기전자 산업 수요가 부각될 때 은 가격이 별도로 강해지는 경우도 있습니다.",
                "금과 은의 비율, 달러 흐름, 실질금리 흐름을 함께 보면 방향성을 해석하는 데 도움이 됩니다."
            ]
        )
    )


@app.route("/dollar-strategy")
def dollar_strategy():
    return render_template(
        "forecast.html",
        **forecast_context(
            "dxy",
            "달러지수 전략 | 달러 강세/약세 대응 아이디어",
            "달러지수 흐름을 기준으로 원자재와의 관계, 달러 강세·약세 대응 아이디어를 정리한 페이지입니다.",
            [
                "달러 강세는 원자재 가격에 부담이 되는 경우가 많아 금·원유와 함께 비교해 보는 것이 좋습니다.",
                "달러 약세 국면에서는 위험자산 선호와 원자재 강세가 동시에 나타나는지 확인하는 투자자도 있습니다.",
                "달러지수는 금리, 경기 기대, 안전자산 선호 심리에 영향을 받으므로 거시 변수와 함께 보는 것이 중요합니다."
            ]
        )
    )


@app.route("/gold-up-assets")
def gold_up_assets():
    return render_template(
        "assets.html",
        **asset_page_context(
            "gold",
            "금 상승 시 참고 자산 | 금 강세 구간 아이디어",
            "금 가격이 강세일 때 함께 보는 자산과 전략 아이디어를 정리한 페이지입니다.",
            [
                {"name": "금 ETF", "desc": "금 가격 방향에 직접 연결되는 대표 참고 자산입니다."},
                {"name": "금 채굴주", "desc": "금 가격 상승 시 실적 기대가 커질 수 있어 함께 주목받는 경우가 있습니다."},
                {"name": "안전자산 비중 확대", "desc": "포트폴리오 내 변동성 완화 목적의 전략으로 함께 사용되기도 합니다."}
            ]
        )
    )


@app.route("/gold-down-assets")
def gold_down_assets():
    return render_template(
        "assets.html",
        **asset_page_context(
            "gold",
            "금 하락 시 참고 자산 | 금 약세 구간 아이디어",
            "금 가격이 약세일 때 참고하는 자산과 전략 아이디어를 정리한 페이지입니다.",
            [
                {"name": "금 인버스 ETF", "desc": "금 가격 하락 방향을 활용하는 구조의 상품을 참고하는 투자자도 있습니다."},
                {"name": "달러 강세 관련 자산", "desc": "금 약세 구간과 달러 강세 흐름을 함께 비교하는 전략이 있습니다."},
                {"name": "방어형 현금 비중", "desc": "방향성이 불리할 때는 현금 비중을 유지하며 다음 신호를 기다리는 방식도 있습니다."}
            ]
        )
    )


@app.route("/oil-up-assets")
def oil_up_assets():
    return render_template(
        "assets.html",
        **asset_page_context(
            "oil",
            "유가 상승 시 수혜 자산 | 원유 강세 구간 아이디어",
            "국제유가 상승 시 함께 참고할 수 있는 자산과 전략 아이디어를 정리한 페이지입니다.",
            [
                {"name": "에너지 ETF", "desc": "유가 상승 흐름과 함께 강세를 보일 수 있는 대표 참고 자산입니다."},
                {"name": "정유주", "desc": "정유 마진과 시장 기대가 반영되는 종목군으로 함께 비교하는 경우가 많습니다."},
                {"name": "탐사·생산 기업", "desc": "원유 가격 상승 시 수익성 기대가 커질 수 있는 업종입니다."}
            ]
        )
    )


@app.route("/oil-down-assets")
def oil_down_assets():
    return render_template(
        "assets.html",
        **asset_page_context(
            "oil",
            "유가 하락 시 참고 자산 | 원유 약세 구간 아이디어",
            "국제유가 하락 시 함께 참고할 수 있는 업종과 전략 아이디어를 정리한 페이지입니다.",
            [
                {"name": "항공주", "desc": "유류비 부담 완화 기대가 생길 수 있어 함께 비교하는 경우가 있습니다."},
                {"name": "운송주", "desc": "에너지 비용 하락이 원가 측면에서 긍정적일 수 있는 업종입니다."},
                {"name": "원가 절감 수혜 업종", "desc": "유가 하락이 비용 구조에 긍정적인 산업군을 함께 검토할 수 있습니다."}
            ]
        )
    )


@app.route("/silver-assets")
def silver_assets():
    return render_template(
        "assets.html",
        **asset_page_context(
            "silver",
            "은 관련 참고 자산 | 은 가격 전략 아이디어",
            "은 가격 흐름과 함께 참고하는 자산과 전략 아이디어를 정리한 페이지입니다.",
            [
                {"name": "은 ETF", "desc": "은 가격 흐름에 직접 연결되는 대표 자산군입니다."},
                {"name": "귀금속 분산 전략", "desc": "금과 은을 함께 보는 분산 관점 전략이 사용되기도 합니다."},
                {"name": "산업 수요 관련 업종", "desc": "은은 산업재 성격도 있어 산업 수요와 함께 보는 해석이 가능합니다."}
            ]
        )
    )


@app.route("/dollar-assets")
def dollar_assets():
    return render_template(
        "assets.html",
        **asset_page_context(
            "dxy",
            "달러지수 관련 참고 자산 | 달러 전략 아이디어",
            "달러지수 흐름과 함께 참고하는 자산과 전략 아이디어를 정리한 페이지입니다.",
            [
                {"name": "달러 강세 수혜 자산", "desc": "달러 강세 환경에서 상대적으로 유리한 자산군을 함께 비교할 수 있습니다."},
                {"name": "원자재 반대 흐름 체크", "desc": "달러와 금·원유가 반대로 움직이는지 비교하면 시장 해석에 도움이 됩니다."},
                {"name": "환율 민감 자산", "desc": "달러 방향성에 민감한 자산군과 업종 흐름을 함께 보는 전략이 있습니다."}
            ]
        )
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
