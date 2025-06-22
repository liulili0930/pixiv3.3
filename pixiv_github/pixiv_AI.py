from openai import OpenAI
import os

with open(fr"{os.getcwd()}\pixiv3.3_app.py","r",encoding="utf-8") as f:
    code = f.read()

def deepseek(problem:str):
    client = OpenAI(api_key="设置你的api_key", base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": f"你是pixiv爬虫软件的客服,你需要辅助此软件为客户解答问题,你不能向任何人透露源代码,以下为pixiv爬虫软件源码:{code}"},
            {"role": "user", "content": problem},
        ],
        stream=False
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    while True:
        a = input("输入问题:")
        if a == "exit":
            break
        print(f"ai回答:\n{deepseek(a)}")