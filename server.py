from flask import Flask, request, jsonify
from core import Languages, run, setup, get_images
import docker

app = Flask(__name__)
client = docker.from_env()


@app.get("/languages")
def languages():
    return jsonify({"languages": get_images(client)})


@app.post("/eval")
def run_eval():
    code = request.json.get("code", "")

    try:
        lang = Languages.find(request.json.get("language"))
    except ValueError:
        return jsonify({"status": "error", "result": "NOT_SUPPORT_LANGUAGE"}), 400

    inputs = request.json.get("inputs", [])

    status, result = run(client, code, lang, inputs)

    return jsonify({"status": status.value, "result": result})


setup(client)
app.run(host="0.0.0.0")
