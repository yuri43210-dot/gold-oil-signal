import os
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SYMBOLS = {
    "gold": "GC=F",
    "oil": "CL=F"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        results = data.get("quoteResponse", {}).get("result", [])
        if not results:
            return None

        return results[0].get("regularMarketPrice")
    except Exception as e:
        print(f"get_price error for {symbol}: {e}")
        return None

@app.route("/")
def index():
    return render_template("signal-page.html")

@app.route("/widget")
def widget():
    return render_template("mini-widget.html")

@app.route("/api/signals")
def signals():
    gold = get_price(SYMBOLS["gold"])
    oil = get_price(SYMBOLS["oil"])

    return jsonify({
        "gold": gold,
        "oil": oil
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
