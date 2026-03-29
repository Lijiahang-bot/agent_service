import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    # 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def get_response(messages):
    completion = client.chat.completions.create(
        model="qwen3.5-flash",
        messages=messages
    )
    return completion.choices[0].message.content

# 初始化 messages
messages = []

# 第 1 轮
messages.append({"role": "user", "content": "推荐一部关于太空探索的科幻电影。"})
print("第1轮")
print(f"用户：{messages[0]['content']}")
assistant_output = get_response(messages)
messages.append({"role": "assistant", "content": assistant_output})
print(f"模型：{assistant_output}\n")

# 第 2 轮
messages.append({"role": "user", "content": "这部电影的导演是谁？"})
print("第2轮")
print(f"用户：{messages[-1]['content']}")
assistant_output = get_response(messages)
messages.append({"role": "assistant", "content": assistant_output})
print(f"模型：{assistant_output}\n")