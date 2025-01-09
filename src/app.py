from flask import Flask, request, jsonify
from flask_cors import CORS  # 导入 CORS
import subprocess
import json
import os
import sys

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
        # 获取当前文件的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建 deepseek_script.py 的绝对路径
        script_path = os.path.join(current_dir, 'deepseek_script.py')

        # 调用 deepseek_script.py，并将 messages 数据传递给它
        # 使用当前Python解释器路径
        result = subprocess.run(
            [sys.executable, script_path, json.dumps(data['messages'])],
            capture_output=True, text=True,
            env=os.environ  # 传递当前环境变量
        )
        print(f"Subprocess stderr: {result.stderr}")  # 打印标准错误

        # 检查脚本是否成功运行
        print(f"Subprocess stdout: {result.stdout}")  # 添加调试日志
        print(f"Subprocess stderr: {result.stderr}")  # 添加调试日志
        print(f"Subprocess return code: {result.returncode}")  # 添加调试日志
        print(f"Full subprocess output: {result}")  # 打印完整子进程对象
        
        if result.returncode != 0:
            return jsonify({'error': result.stderr}), 500

        # 尝试解析脚本输出为JSON
        try:
            output = json.loads(result.stdout)
            return jsonify(output)
        except json.JSONDecodeError:
            # 如果解析失败，返回原始输出
            return jsonify({'output': result.stdout})

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
