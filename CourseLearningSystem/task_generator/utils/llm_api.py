import os
from openai import OpenAI
from config import BASE_URL, DEEPSEEK_API_KEY

def call_llm(prompt):
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请先在环境变量或系统设置中配置大模型 API Key。")
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=BASE_URL
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.6
    )
    return response.choices[0].message.content
