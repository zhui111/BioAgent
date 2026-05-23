# utils/ai_grader.py
"""
AI 评分 & 解析模块
- 对用户的简答题回答进行智能评分
- 为错题生成深度解析
- 动态生成选择题选项
"""
import json
from langchain_deepseek import ChatDeepSeek
from utils.config import DEEPSEEK_API_KEY


def _get_llm(temperature: float = 0.0):
    return ChatDeepSeek(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        temperature=temperature,
        max_tokens=1024
    )


def grade_answer(question: str, std_answer: str, user_answer: str) -> dict:
    """
    对用户的简答回答评分，返回：
    {
        "score": 8.5,        # 0~10
        "is_correct": True,  # score >= 6 视为正确
        "feedback": "...",   # 具体点评
        "key_missing": "...", # 缺失的核心知识点
    }
    """
    llm = _get_llm(temperature=0.0)
    prompt = f"""你是一位严格但公平的生物医学教授，正在批改学生的简答题。

【题目】：{question}
【标准答案】：{std_answer}
【学生回答】：{user_answer}

评分标准：
- 10分：完全正确，涵盖所有核心知识点，术语准确
- 7-9分：基本正确，核心概念准确，细节略有遗漏
- 4-6分：方向正确，但缺失重要知识点或有部分错误
- 1-3分：有少量正确内容，但存在明显错误
- 0分：完全错误或未作答

请严格按以下JSON格式输出，不要有任何其他文字：
{{"score": 8.5, "is_correct": true, "feedback": "一到两句具体点评", "key_missing": "缺失的核心知识点，若无则为空字符串"}}"""

    try:
        resp = llm.invoke(prompt).content
        start = resp.find('{')
        end = resp.rfind('}') + 1
        result = json.loads(resp[start:end])
        result["score"] = float(result.get("score", 0))
        result["is_correct"] = result["score"] >= 6.0
        return result
    except Exception as e:
        return {"score": 0.0, "is_correct": False,
                "feedback": f"AI评分失败: {e}", "key_missing": ""}


def generate_mistake_analysis(question: str, std_answer: str,
                               user_answer: str, rag_context: str = "") -> str:
    """
    为错题生成深度解析，包含：
    - 正确答案的核心逻辑
    - 学生错误原因分析
    - 记忆技巧/助记方法
    - 相关延伸知识点
    """
    llm = _get_llm(temperature=0.3)
    context_section = f"\n【教材相关原文】：\n{rag_context}\n" if rag_context else ""
    prompt = f"""你是一位耐心的生物医学导师，正在为学生解析一道错题。
{context_section}
【题目】：{question}
【标准答案】：{std_answer}
【学生的错误回答】：{user_answer}

请生成一份结构清晰的错题解析，包含以下部分（用中文）：

## 💡 核心知识点
（用2-3句话解释这道题考察的核心概念）

## ❌ 错误原因分析
（分析学生可能的误解或知识盲点）

## ✅ 正确解题思路
（分步骤讲解标准答案的逻辑）

## 🔗 相关延伸
（列举1-2个与本题相关的知识点，帮助构建知识网络）

## 🧠 记忆技巧
（提供一个简短的助记方法或类比）"""

    try:
        return llm.invoke(prompt).content
    except Exception as e:
        return f"解析生成失败：{e}"


def generate_choice_options(question: str, correct_answer: str, topic: str = "") -> list:
    """
    为简答题动态生成4个选项（1个正确答案 + 3个干扰项），
    返回 ["选项A内容", "选项B内容", "选项C内容", "选项D内容"]
    正确答案随机插入其中。
    """
    llm = _get_llm(temperature=0.7)
    prompt = f"""你是一位生物医学题目命题专家。请为以下题目生成3个高质量的干扰选项（错误答案）。

【题目】：{question}
【正确答案】：{correct_answer}
知识点领域：{topic or "生物医学"}

要求：
- 干扰项要有迷惑性，像真实考试的错误选项（似是而非）
- 干扰项长度与正确答案相近
- 不要太明显是错的

严格按以下JSON格式输出，不要有其他文字：
{{"distractors": ["干扰项1", "干扰项2", "干扰项3"]}}"""

    try:
        resp = llm.invoke(prompt).content
        start = resp.find('{')
        end = resp.rfind('}') + 1
        data = json.loads(resp[start:end])
        distractors = data.get("distractors", [])[:3]

        # 组合选项，正确答案随机插入
        import random
        options = distractors + [correct_answer]
        random.shuffle(options)
        return options
    except Exception:
        # 生成失败则降级为简答题
        return []


import random

def generate_dynamic_question(rag_chain, topic_hint: str = "") -> dict:
    """
    利用 RAG 链从知识库动态生成一道新题（不依赖预存题库）
    返回 {"question": "...", "answer": "...", "topic": "..."}
    """
    llm = _get_llm(temperature=0.8)
    
   
    if topic_hint:
        seed_prompt = f"{topic_hint} 核心概念 原理"
    else:
        # 随机挑选一些生物学核心领域作为检索词，保证每次 RAG 抽取的片段不同
        random_seeds = [
            "DNA复制机制", "蛋白质合成过程", "细胞信号传导", 
            "基因表达调控", "酶促反应动力学", "细胞周期与凋亡", 
            "基因突变与修复", "表观遗传学", "代谢途径", "免疫应答机制"
        ]
        seed_prompt = random.choice(random_seeds)
        
    try:
        # 用 RAG 链检索相关内容
        rag_result = rag_chain({"query": seed_prompt})
        
        # 2. 修复暴力的字符截断 Bug：只取前 2 个完整文档，保持语境完整
        docs = rag_result.get("source_documents", [])[:3]
        context = "\n".join(doc.page_content for doc in docs)

        # 3. 修复“图XX”不可见 Bug & 强化 JSON 输出稳定性
        prompt = f"""你是一位专业的大学分子生物学教授。请根据以下提供的教材片段，生成一道高质量的简答题。
        
        如果你收到了特定的知识点要求，请侧重该部分：{topic_hint}

教材片段：
{context}

出题核心要求（必须严格遵守）：
1. 考察对核心概念的深层理解，而非死记硬背。
2. 【上下文独立性】：问题必须是完全独立的！绝对**不能**包含或引用任何“图X-X”、“表X”、“见上图”、“本章提到”等无法脱离原文独立存在的描述。
3. 【图表转换】：如果教材内容中提到了图表，请提取其背后的【文字原理】来出题，而不是针对图表本身提问。
4. 问题明确，有唯一的正确答案方向，统一用中文作答。
5. 【格式严格】：务必直接输出合法的纯 JSON 对象，不要使用 Markdown 语法（如 ```json ），也不要输出任何解释性文字。

严格按JSON格式输出：
{{"question": "...", "answer": "...", "topic": "核心知识点标签"}}"""

        resp = llm.invoke(prompt).content
        
        # 增强的 JSON 解析（忽略大模型可能带有的冗余文本）
        start = resp.find('{')
        end = resp.rfind('}') + 1
        if start != -1 and end != -1:
            return json.loads(resp[start:end])
        else:
            raise ValueError("未找到合法的 JSON 结构")
            
    except Exception as e:
        return {"question": "", "answer": "", "topic": "", "error": str(e)}