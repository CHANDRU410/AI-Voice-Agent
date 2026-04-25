from flask import Flask, jsonify
from db import get_all_calls, get_call, get_high_intent_calls,get_medium_intent_calls,get_low_intent_calls
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

@app.route("/calls", methods=["GET"])
def calls():
    data = get_all_calls()
    for d in data:
        d["_id"] = str(d["_id"])
        d["language"] = d.get("language", "en")
    return jsonify(data)


@app.route("/calls/<call_sid>", methods=["GET"])
def call_detail(call_sid):
    data = get_call(call_sid)
    if data:
        data["_id"] = str(data["_id"])
        data["language"] = data.get("language", "en")
    return jsonify(data)


@app.route("/calls/high", methods=["GET"])
def high_intent():
    data = get_high_intent_calls()
    for d in data:
        d["_id"] = str(d["_id"])
        d["language"] = d.get("language", "en")
    return jsonify(data)

@app.route("/calls/medium", methods=["GET"])
def medium_intent():
    data = get_medium_intent_calls()
    for d in data:
        d["_id"] = str(d["_id"])
        d["language"] = d.get("language", "en")
    return jsonify(data)


@app.route("/calls/low", methods=["GET"])
def low_intent():
    data = get_low_intent_calls()
    for d in data:
        d["_id"] = str(d["_id"])
        d["language"] = d.get("language", "en")
    return jsonify(data)


if __name__ == "__main__":
    app.run(port=5001)