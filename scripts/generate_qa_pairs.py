# scripts/generate_qa_pairs.py
import pickle
import json
import random
import sys
sys.path.append('.')
from langchain_deepseek import ChatDeepSeek
from utils.config import DEEPSEEK_API_KEY, CHUNKS_PKL_PATH

def generate_qa_pairs(num_samples=200):
    # 加载分块
    with open(CHUNKS_PKL_PATH, "rb") as f:
        chunks = pickle.load(f)

    # 随机抽取一部分块来生成QA
    sampled_chunks = random.sample(chunks, min(num_samples, len(chunks)))

    llm = ChatDeepSeek(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        temperature=0.7
    )

    qa_pairs = []
    for i, chunk in enumerate(sampled_chunks):
        text = chunk.page_content[:800]  # 限制长度
        prompt = f"""你是一位生物医学教授。请根据以下来自教材的文本（可能是中文或英文），生成一个高质量的问题和对应的答案。
问题应考查对核心概念的理解，而非单纯的事实记忆。
请统一用中文输出问题和答案。
严格按照JSON格式输出，不要有其他文字： {{"question": "...", "answer": "..."}}

教材文本: {text}"""
        try:
            response = llm.invoke(prompt)
            # 解析JSON
            content = response.content
            # 简单清理，提取JSON部分
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = content[start:end]
                qa = json.loads(json_str)
                qa_pairs.append(qa)
                print(f"Generated {i+1}/{len(sampled_chunks)}")
        except Exception as e:
            print(f"Error at chunk {i}: {e}")
            continue

    # 保存为训练格式（instruction-output）
    training_data = [{"instruction": qa["question"], "output": qa["answer"]} for qa in qa_pairs]
    with open("data/training_data.json", "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(training_data)} QA pairs to data/training_data.json")

if __name__ == "__main__":
    generate_qa_pairs()