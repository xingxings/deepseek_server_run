from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import time
from deepseek_script import call_deepseek_api

app = Flask(__name__)
CORS(app, resources={
    r"/run-python": {
        "origins": ["http://47.93.160.85"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

@app.route('/')
def index():
    return "Welcome to DeepSeek Server!"

@app.route('/run-python', methods=['POST', 'OPTIONS'])
def run_python():
    if request.method == 'OPTIONS':
        # 处理预检请求
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://47.93.160.85')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    # 内存监控
    import resource
    mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
    print(f"Memory usage: {mem_usage:.2f} MB")

    # 获取来自甲服务器的 JSON 数据
    data = request.json
    print(f"Received data: {data}")  # 添加调试日志

    # 检查输入数据是否包含必要的字段
    if 'messages' not in data:
        print("Missing 'messages' field")  # 添加调试日志
        return jsonify({'error': 'Missing "messages" field in request'}), 400

    # 错误重试机制
    max_retries = 3
    retry_delay = 5  # 初始延迟5秒
    max_delay = 30  # 最大延迟30秒

    for attempt in range(max_retries):
        try:
            start_time = time.time()
            # 直接调用 deepseek_script 中的函数，增加超时设置
            result = call_deepseek_api(data['messages'], timeout=30)
            elapsed_time = time.time() - start_time
            print(f"API call succeeded in {elapsed_time:.2f} seconds")
            return jsonify(result)

        except Exception as e:
            error_msg = str(e)
            print(f"Attempt {attempt + 1} failed: {error_msg}")
            if attempt < max_retries - 1:
                # 指数退避算法
                delay = min(retry_delay * (2 ** attempt), max_delay)
                print(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
                continue
                
            # 捕获并返回异常信息
            print(f"All attempts failed: {error_msg}")  # 添加错误日志
            return jsonify({
                'error': error_msg,
                'type': type(e).__name__,
                'attempts': attempt + 1
            }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
