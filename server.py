from flask import Flask, request, jsonify
from core import Languages, run, setup
from subprocess import check_output

app = Flask(__name__)


@app.get("/languages")
def languages():
    images = (
        check_output('docker images langlang --format "{{.Tag}}"', shell=True)
        .decode()
        .rstrip()
        .split("\n")
    )
    return jsonify({"languages": images})


@app.post("/eval")
def run_eval():
    code = request.json.get("code", "")

    try:
        lang = Languages.find(request.json.get("language"))
    except ValueError:
        return jsonify({"status": "error", "result": "NOT_SUPPORT_LANGUAGE"}), 400

    status, result = run(code, lang)

    return jsonify({"status": status.value, "result": result})


setup()
app.run()
