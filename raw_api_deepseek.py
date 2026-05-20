import os
import json

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
print(API_KEY)
API_URL = "https://api.deepseek.com/chat/completions"
import requests  # 使用 requests 替代 urllib

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/chat/completions"

def call_api(prompt: str) -> str:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {API_KEY}",
    }
    
    payload = {
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 1000,
    }
    
    # requests 会自动处理好大部分环境的 SSL 证书
    response = requests.post(API_URL, json=payload, headers=headers)
    response.raise_for_status()  # 如果状态码不对直接抛出异常
    
    result = response.json()
    return result['choices'][0]['message']['content']
    
if __name__ == "__main__":
    # 测试：让它分析一个项目
    print("=" * 60)
    print("测试：让 AI 分析当前项目的代码结构")
    print("=" * 60)
    response = call_api("请分析当前项目的目录结构和代码质量，给出改进建议。")
    print(response)
    print("\n" + "=" * 60)
    print("观察：AI 能看到你的项目文件吗？")
    print("=" * 60)