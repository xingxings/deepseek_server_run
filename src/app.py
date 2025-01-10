from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import time
import datetime
import psutil
import gc
from deepseek_script import call_deepseek_api

def log_memory_usage():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"Memory usage: RSS={mem_info.rss/1024/1024:.2f}MB VMS={mem_info.vms/1024/1024:.2f}MB")

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return "Welcome to DeepSeek Server!"

@app.route('/run_python', methods=['POST', 'OPTIONS'])
def run_python():
    if request.method == 'OPTIONS':
        # 处理预检请求
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://47.93.160.85')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    # 获取并验证请求数据
    data = request.json
    if not data or 'messages' not in data:
        return jsonify({
            'response': 'Invalid request format',
            'metadata': {
                'status': 'error',
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            }
        }), 400

    # 提取用户消息
    user_messages = [msg['text'] for msg in data['messages'] if msg['sender'] == 'user']
    if not user_messages:
        return jsonify({
            'response': 'No user message found',
            'metadata': {
                'status': 'error', 
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            }
        }), 400

    try:
        # 调用DeepSeek API
        result = call_deepseek_api(user_messages)
        
        # 构造响应
        return jsonify({
            'response': result['choices'][0]['message']['content'],
            'metadata': {
                'status': 'success',
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            }
        })
    except Exception as e:
        return jsonify({
            'response': f'Error processing request: {str(e)}',
            'metadata': {
                'status': 'error',
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
