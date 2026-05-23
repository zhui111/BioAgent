# scripts/run_evaluation.py
import json
import pandas as pd
import sys
import os
sys.path.append('.')
from langchain_deepseek import ChatDeepSeek
from utils.rag_chain import load_rag_chain
from utils.config import DEEPSEEK_API_KEY

def build_judge_prompt(question, ground_truth, baseline_ans, rag_ans):
    return f"""你是一位严谨的生物医学领域教授，正在批改学生的考试答案。
知识背景说明：本题的知识库来源包含中文和英文教材，模型回答统一为中文。
请根据【标准答案】，对【模型A】和【模型B】的回答分别从以下三个维度独立打分（每项1-10分）：

评分维度：
1. 事实准确性（Accuracy）：生物学事实是否正确？有无错误或捏造内容？
2. 完整性（Completeness）：是否涵盖了标准答案的核心知识点？
3. 术语精准性（Precision）：专业术语使用是否规范（中英文术语均可接受）？

最终得分：Final = Accuracy×0.5 + Completeness×0.3 + Precision×0.2

注意事项：
- 答案更长不代表更好，只看内容质量
- 两个模型必须独立评分，不要相互比较后再打分
- 中英文专业术语混用是正常现象，不应扣分
- 如果某模型有明显错误事实，Accuracy不得超过5分

请严格按照以下JSON格式输出，不要输出任何其他文字：
{{"ModelA": {{"accuracy": 0, "completeness": 0, "precision": 0, "final": 0.0, "reason": "一句话理由"}}, "ModelB": {{"accuracy": 0, "completeness": 0, "precision": 0, "final": 0.0, "reason": "一句话理由"}}}}

【问题】：{question}
【标准答案】：{ground_truth}
【模型A（无知识库baseline）的回答】：{baseline_ans}
【模型B（RAG知识库）的回答】：{rag_ans}"""

def parse_scores(score_response: str):
    """安全解析JSON，返回 (baseline_score, rag_score) 或 (None, None)"""
    try:
        start = score_response.find('{')
        end = score_response.rfind('}') + 1
        scores = json.loads(score_response[start:end])
        a = float(scores["ModelA"]["final"])
        b = float(scores["ModelB"]["final"])
        reason_a = scores["ModelA"].get("reason", "")
        reason_b = scores["ModelB"].get("reason", "")
        return a, b, reason_a, reason_b
    except Exception as e:
        print(f"    ⚠️ JSON解析失败: {e}")
        print(f"    原始返回: {score_response[:300]}")
        return None, None, "", ""


def evaluate_models(sample_size=20):
    # 1. 加载测试集
    with open("data/training_data.json", "r", encoding="utf-8") as f:
        test_data = json.load(f)[:sample_size]
    print(f"✅ 加载 {len(test_data)} 条测试数据")

    # 2. 初始化模型
    baseline_llm = ChatDeepSeek(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        temperature=0.1   # 问答：低随机性
    )
    rag_agent = load_rag_chain()

    judge_llm = ChatDeepSeek(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        temperature=0.0   # 裁判：完全确定性，减少随机波动
    )

    results = []
    skip_count = 0

    for i, item in enumerate(test_data):
        question = item["instruction"]
        ground_truth = item["output"]

        print(f"\n[{i+1}/{len(test_data)}] 问题: {question[:60]}...")

        # 获取两个模型的回答
        try:
            print("    → Baseline 回答中...")
            baseline_ans = baseline_llm.invoke(question).content

            print("    → RAG 回答中...")
            rag_ans = rag_agent({"query": question})["result"]
        except Exception as e:
            print(f"    ❌ 获取回答失败，跳过: {e}")
            skip_count += 1
            continue

        # 裁判打分
        judge_prompt = build_judge_prompt(question, ground_truth, baseline_ans, rag_ans)

        try:
            print("    → 裁判打分中...")
            score_response = judge_llm.invoke(judge_prompt).content
            a_score, b_score, reason_a, reason_b = parse_scores(score_response)

            if a_score is None:
                skip_count += 1
                continue

            print(f"    ✓ Baseline={a_score:.1f}  RAG={b_score:.1f}")
            results.append({
                "Question": question[:100],
                "Baseline_Score": a_score,
                "RAG_Score": b_score,
                "Baseline_Reason": reason_a,
                "RAG_Reason": reason_b,
                "RAG_Win": b_score > a_score,      # 方便后续统计胜率
            })

        except Exception as e:
            print(f"    ❌ 裁判出错，跳过: {e}")
            skip_count += 1

    # 保存结果
    df = pd.DataFrame(results)
    df.to_csv("data/evaluation_results.csv", index=False, encoding="utf-8-sig")

    # 打印汇总
    print("\n" + "="*50)
    print(f"✅ 评估完成！成功 {len(df)} 题，跳过 {skip_count} 题")
    print(f"   Baseline 平均分：{df['Baseline_Score'].mean():.2f}")
    print(f"   RAG 平均分：    {df['RAG_Score'].mean():.2f}")
    rag_win_rate = df['RAG_Win'].sum() / len(df) * 100
    print(f"   RAG 胜率：      {rag_win_rate:.1f}%")
    print("="*50)

if __name__ == "__main__":
    evaluate_models()