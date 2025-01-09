from flask import Flask, request, jsonify
from flask_cors import CORS  # 导入 CORS
import json
import os
from deepseek_script import call_deepseek_api

app = Flask(__name__)

# 启用 CORS，允许所有域名访问
CORS(app)

@app.route('/')
def index():
    return "Welcome to DeepSeek Server!"

@app.route('/run-python', methods=['POST'])
def run_python():
    # 获取来自甲服务器的 JSON 数据
    data = request.json
    print(f"Received data: {data}")  # 添加调试日志

    # 检查输入数据是否包含必要的字段
    if 'messages' not in data:
        print("Missing 'messages' field")  # 添加调试日志
        return jsonify({'error': 'Missing "messages" field in request'}), 400

    try:
        # 直接调用 deepseek_script 中的函数
        result = call_deepseek_api(data['messages'])
        return jsonify(result)

    except Exception as e:
        # 捕获并返回异常信息
        error_msg = str(e)
        print(f"Error occurred: {error_msg}")  # 添加错误日志
        return jsonify({
            'error': error_msg,
            'type': type(e).__name__
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
