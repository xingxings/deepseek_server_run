from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Welcome to DeepSeek Server!"

@app.route('/run-python', methods=['POST'])
def run_python():
    # 获取来自甲服务器的 JSON 数据
    data = request.json

    # 检查输入数据是否包含必要的字段
    if 'messages' not in data:
        return jsonify({'error': 'Missing "messages" field in request'}), 400

    try:
        # 获取当前文件的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建 deepseek_script.py 的绝对路径
        script_path = os.path.join(current_dir, 'deepseek_script.py')

        # 调用 deepseek_script.py，并将 messages 数据传递给它
        result = subprocess.run(
            ['python3', script_path, json.dumps(data['messages'])],
            capture_output=True, text=True
        )

        # 检查脚本是否成功运行
        if result.returncode != 0:
            return jsonify({'error': result.stderr}), 500

        # 解析脚本的输出
        output = json.loads(result.stdout)

        # 返回处理后的结果
        return jsonify({'output': output})

    except Exception as e:
        # 捕获并返回异常信息
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)