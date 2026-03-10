import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SYMBOLS = {
    "gold": "GC=F",
    "oil": "CL=F"
}

def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    r = requests.get(url)
    data = r.json()
    price = data["quoteResponse"]["result"][0]["regularMarketPrice"]
    return price

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
    app.run(host="0.0.0.0", port=10000)
