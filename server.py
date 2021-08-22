from flask import Flask, request, jsonify
from core import Languages, run, setup

app = Flask(__name__)

@app.post('/eval')
def run_eval():
    code = request.json.get('code', '')

    try:
        lang = Languages.find(request.json.get('language'))
    except ValueError:
        return jsonify({'status': 'error', 'result': 'NOT_SUPPORT_LANGUAGE'}), 400

    status, result = run(code, lang)
    
    return jsonify({'status': status.value, 'result': result})

setup()
app.run()