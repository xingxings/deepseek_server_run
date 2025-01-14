import sys
import json
import logging
import tracemalloc
import gc
from openai import OpenAI
from dotenv import load_dotenv
import os
import psutil
import time


role_sys = "你是一个富有耐心，和蔼可亲的高中数学老师，任务是回答学生提出的数学问题。"

scope_def = """
            回答问题依据的知识范围：
            1. 知识范围：请以高中数学知识为基础，确保回答内容适合高中学生理解；
            2. 问题范围：仅回答与数学相关的问题。如果学生提问数学无关的问题，请礼貌拒绝；
            3. 如果你发现这个问题超出了你的能力范围，请回答“我有点笨，无法解决这个问题”。
"""

style_req = """
            回答风格要求：
            3. 步骤化的回答：将回答分为清晰的步骤，每一步包含三个方面，第一方面是依据什么信号执行什么操作，第二方面是计算和推导的详细过程，第三方面是每一步得到的结果，并且用 box 展示出来；
            4. 术语和符号要求：不要使用高中学生不熟悉的名词和符号；
            6. 计算和化简方面要求：必须要有详细的计算整理过程，坚决不允许跳过任何中间步骤；
"""

format_req = """
            回答格式要求：
            7. 结果表示：结果一定要化为最简形式，如果结果是无理数，要进行分母有理化，结果不可以用无限小数表示；
            8. 数学公式：使用 Latex 展示数学公式，行内数学公式使用 $，居中数学公式使用 $$ 表示，一定不要使用 \( 和 \) 或 \[ 和 \]；
            9. 公式过长时，一定要分行展示，分行时，符号要放在行首；
            不推荐：
            $$
            S_n - T_n = (1 + 2 + 3 + \cdots + n) - (2^1 + 2^2 + 2^3 + \cdots + 2^n) 
            $$
            推荐：
            $$
            \begin{aligned}
            S_n - T_n & = (1 + 2 + 3 + \cdots + n) \\
            & - (2^1 + 2^2 + 2^3 + \cdots + 2^n) 
            \end{aligned}
            $$
            10. 对齐要求：多个居中的公式堆叠在一起时，一定要放到同一个 $$...$$ 中，并用 aligned 进行对齐；
            推荐：
            $$
            \begin{aligned}
            a^2 & = 1 - b^2 \\
            & = 1 - (\dfrac{1}{3})^2 \\
            & = 1 - \dfrac{1}{9} \\
            & = \dfrac{8}{9}
            \end{aligned}
            $$
            不推荐：
            $$a^2 = 1- b^2$$
            $$a^2 = 1 - (\dfrac{1}{3})^2$$
            $$a^2 = 1 - \dfrac{1}{9}$$
            $$a^2 = \dfrac{8}{9}$$
            11. 符号要求：使用 \geqslant 表示 \geq，\leqslant 表示\leq，\dfrac 表示 \frac，不要使用 \hline；
            12. 求和操作一定不能用 \sum 符号表示，请用展开式来表示，
            示例：
            不推荐：$\sum_{k=1}^{n} k$,
            推荐：$1+2+3+...+n$。
"""

length_control = "请在2000 字内回答问题，若回答超过 2000 字，请重新回答"


def sug_tip():
    sug_prompt = """
    如果学生需要一些提示，请给出提示，要求如下：
        1. 只生成一步提示，不要一次性给出很多提示，并且告知学生，如果需要更多提示，请继续提问；
        2. 如果之前给出过提示，请结合之前的提示，给出新的提示，避免给出重复的提示，这样对学生没有意义；
        3. 如果提示的信息已经足够解决问题，请告知学生，信息已经足够，请结合提示信息，耐心思考，可以得到正确答案。
        3. 提示过程中，一定一定不能直接给出题目的答案，这样会给学生作弊提供空间，
        4. 请评估本次提示在解决这个问题中的作用，以百分数来计量，输出的格式为：
            <deductedScore>百分数</deductedScore>
            标签前面请不要添加关于评估作用的描述；
    """
    return sug_prompt


def sug_thought():
    sug_prompt = """
        如果学生需要大概的思路，请结合学生所做的题目，给出大概思路。要求如下：
            1. 给出大致思路，不用给出太多的细节，和题目的详解要去别开；
            2. 思路的描述要清晰，必要时请给出相关的知识点；
            3. 一定一定不要直接给出答案，这样会给学生作弊提供空间；
            4. 如果之前有给出过提示，请结合之前的提示，给出合理的思路信息，避免让学生感觉没有价值；
            5. 请评估大概思路的提示在解决这个问题中的作用，以百分数来计量，输出的格式为：
                <deductedScore>百分数</deductedScore>
                标签前面请不要添加关于评估作用的描述；
    """
    return sug_prompt

def sug_solution():
    sug_prompt = """
        如果学生想知道这道题的解题思路和步骤，请给予步骤化的回答，要求：
            1. 步骤清晰，解释清楚。
            2. 每一步依据这样的结构进行回答：依据什么信息，执行什么动作，得到什么结果，
            3. 计算、整理、化简等数学过程，一定要非常的详细，不要跳步，以免让学生不理解。
            4. 评估详细的解题步骤在解决这个问题中的作用，以百分数来计量，输出的格式为：
                <deductedScore>百分数</deductedScore>
                标签前面请不要添加关于评估作用的描述；
    """
    return sug_prompt

def sug_misconception():
    sug_prompt = """
        如果学生想知道自己的思路是否正确，要求指出错误思路，请结合学生回答的正误情况、题目本身、错误选项和正确选项给予回答，要求：
            1. 对每个选项进行详细的分析，说明正确或错误的原因；
            2. 猜测学生可能的错误思路，并给与分析；
            3. 措辞更为温和一下，并在最后给学生以肯定和鼓励
    """
    return sug_prompt

def sug_summary():
    sug_prompt = """
        如果学生问及题目涉及到哪些数学知识点，请写出知识点总结，要求如下：
            1. 对每个步骤的知识点进行总结，包括基于什么信号想到的，起到了什么作用；
            2. 在每一步中，列举知识点的常见的使用情景，并举出简单的例子；
            3. 如果之前有生成类似题目，请将原题目和生成的新问题一起进行分析；
            4. 最后给于学生以鼓励和肯定；
    """
    return sug_prompt

def sug_analogue():
    sug_prompt = """
        如果学生想要得到一道和题目类似的新题目，请生成一个相似的新问题，要求：
            1. 新问题和学生所问的问题类似，只是数值或者条件有所改变； 
            2. 新问题必须具备合理性，不可以出现无解的情况；
            3. 数值设计要合理，让学生在解答过程不需要复杂的计算，不能超出知识范围；
            4. 鼓励学生独立的去尝试解决这个问题；
    """
    return sug_prompt


func_call = [
    {
        "type": "function", 
        "function": {
            "name": "sug_tip",
            "description": "当学生问及提示相关的问题时，请调用这个函数",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "sug_thought",
            "description": "当学生问及提示思路方面的问题时，能更好的帮助回答相关的问题",
            "parameters": {
                "type": "object",
                "properties": {} 
            },
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "sug_solution",
            "description": "当学生问及提示解题步骤和详细答案方面的问题时，能更好的帮助回答相关的问题",
            "parameters": {
                "type": "object",
                "properties": {} 
            },
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "sug_misconception",
            "description": "当学生问及涉及错误方面的问题时，能更好的帮助回答相关的问题",
            "parameters": {
                "type": "object",
                "properties": {} 
            },
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "sug_summary",
            "description": "当学生问及总结知识点方面的问题时，能更好的帮助回答相关的问题",
            "parameters": {
                "type": "object",
                "properties": {} 
            },
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "sug_analogue",
            "description": "当学生想要类似的新题目时，能更好的帮助回答相关的问题",
            "parameters": {
                "type": "object",
                "properties": {} 
            },
        }
    }
]


# 加载环境变量
try:
    if not load_dotenv():
        raise EnvironmentError("Failed to load .env file")
    
    # 初始化日志
    # 初始化内存跟踪
    tracemalloc.start()
    
    # 配置日志
    logging.basicConfig(
        level=logging.WARNING,  # 降低日志级别
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('deepseek.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # 设置内存监控
    process = psutil.Process(os.getpid())
    
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.debug(f"Environment variables: {os.environ}")

    # 获取API密钥
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
    
    logger.info("Initializing DeepSeek client")
    client = OpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com",
        max_retries=3,
        timeout=45
    )
except Exception as e:
    logger.error(f"Initialization failed: {str(e)}")
    sys.exit(1)

def call_deepseek_api(data, timeout=45):
    """调用DeepSeek API并返回结果
    Args:
        data: 要发送的消息列表
        timeout: API调用超时时间，默认45秒
    """
    # 内存监控
    mem_before = process.memory_info().rss
    snapshot1 = tracemalloc.take_snapshot()
    max_retries = 3
    retry_delay = 5  # 初始延迟5秒
    max_delay = 45  # 最大延迟30秒

    for attempt in range(max_retries):
        try:
            # 验证输入参数
            if not data:
                raise ValueError("Data cannot be empty")
            
            # 题目信息
            problems_info = f"""
                学生当前所做的题目是：{data['context']['problem']['content']}。
                题目的正确选项是： {', '.join(map(str, data['context']['problem']['right_results']))}。
                题目的错误选项是：{', '.join(map(str, data['context']['problem']['wrong_results']))}。
                学生的答题结果是：{'正确的' if data['context']['isCorrect'] else '错误的'}。
                题目的答案解析是：{'。'.join(map(lambda item: f'{item["content"]}。{item["content"]}', data['context']['problem']['solution']))}。
            """

            # system prompt
            system_role = {"role": "system", "content": f"""
                {role_sys}。
                {scope_def}。
                {style_req}。
                {format_req}。
                {length_control}。
                {problems_info}。
            """}
                
            # 处理 data 中的 messages
            all_roles = []

            all_roles.append(system_role)

            for message in data['messages']:
                if message['sender'] == 'user':
                    role = {
                        "role": "user", "content": message['text']
                    }
                    all_roles.append(role)

                if message['sender'] == 'ai':
                    role = {
                        "role": "assistant", "content": message['text']
                    }
                    all_roles.append(role)
                
            logger.info(f"Calling DeepSeek API with timeout={timeout}s (attempt {attempt + 1})")

            # 调用 DeepSeek API
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages= all_roles,
                tools=func_call,
                stream=False,
                temperature=0,
                timeout=timeout
            )

            if response.choices[0].finish_reason == 'tool_calls':
                called_func = globals()[response.choices[0].message.tool_calls[0].function.name]
                sug_prompt = called_func()
                for item in all_roles:
                    if item['role'] == 'system':
                        item['content'] += sug_prompt

                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages = all_roles,
                    temperature=0,
                    stream=False,
                    timeout=timeout
                )
            
            if not response.choices:
                raise ValueError("No response from DeepSeek API")
                
            logger.info("Successfully received response from DeepSeek API")
            result = {
                'id': response.id,
                'object': response.object,
                'created': response.created,
                'model': response.model,
                'choices': [{
                    'message': {
                        'content': choice.message.content
                    }
                } for choice in response.choices],
                'usage': response.usage.dict()
            }
            
            # 内存监控和清理
            mem_after = process.memory_info().rss
            snapshot2 = tracemalloc.take_snapshot()
            
            # 记录内存使用情况
            logger.warning(f"Memory usage: {mem_after - mem_before} bytes")
            
            # 显示内存分配差异
            top_stats = snapshot2.compare_to(snapshot1, 'lineno')
            for stat in top_stats[:5]:
                logger.warning(stat)
            
            # 显式清理
            del response
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"API call failed (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                delay = min(retry_delay * (2 ** attempt), max_delay)
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
                continue
                
            raise Exception(f"All attempts failed: {str(e)}")

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
    result = call_deepseek_api(input_data)
    
    # 输出结果（JSON 格式）
    # print(json.dumps(result))
