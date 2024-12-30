import sys
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 初始化 DeepSeek 客户端
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

def call_deepseek_api(messages):
    # 调用 DeepSeek API
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=False,
        temperature=0.2
    )
    # 返回 DeepSeek 的回复
    return response.choices[0].message.content

if __name__ == '__main__':
    # 从命令行参数中获取 messages 数据
    input_data = json.loads(sys.argv[1])
    
    # 确保 messages 是一个数组
    if isinstance(input_data, dict) and 'messages' in input_data:
        messages = input_data['messages']
    elif isinstance(input_data, list):
        messages = input_data
    else:
        raise ValueError("Invalid input format: expected a list or a dictionary with 'messages' key")
    
    # 调用 DeepSeek API
    result = call_deepseek_api(messages)
    
    # 输出结果（JSON 格式）
    print(json.dumps(result))