from flask import Flask, request, jsonify
from core import Languages, run

app = Flask(__name__)

@app.post('/eval')
def run_eval():
    result = run(request.json['code'], Languages.find(request.json['language']))
    
    return result

app.run()