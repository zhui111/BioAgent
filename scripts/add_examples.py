"""
为雅思/专业词汇批量生成高质量例句
使用 DeepSeek LLM 根据词性和分类动态生成例句
支持清空旧模板例句并重新生成
"""
import sys
import json
import sqlite3
import time
from typing import Optional, Tuple

sys.path.append('.')

# 引入已有的 DeepSeek 配置
from utils.config import DEEPSEEK_API_KEY
from langchain_deepseek import ChatDeepSeek

def generate_example_with_llm(word: str, translation: str, category: str) -> Optional[Tuple[str, str]]:
    """
    使用大语言模型智能生成例句，兼顾词性、语境和中文翻译
    """
    llm = ChatDeepSeek(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        temperature=0.7
    )
    
    context_hint = category if category else "通用雅思"
    prompt = f"""你是一位严谨的英语词汇老师。请为单词生成一个高质量的英文例句及其中文翻译。

单词：{word}
释义：{translation}
语境分类：{context_hint}

要求：
1. 准确判断该单词的词性（名词、动词、形容词等），确保在例句中的语法完全正确。
2. 例句要自然、地道，且尽量符合【{context_hint}】的学科背景或应用场景。
3. 难度适中，适合大学生或雅思考生学习。
4. 严格按照以下JSON格式输出，不要包含任何其他文字：
{{"example_en": "英文例句", "example_cn": "中文翻译"}}"""

    try:
        response = llm.invoke(prompt).content
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end != 0:
            data = json.loads(response[start:end])
            if data.get("example_en") and data.get("example_cn"):
                return data["example_en"], data["example_cn"]
        return None
    except Exception as e:
        print(f"  ❌ LLM生成失败: {e}")
        return None

def clear_old_examples():
    """清空数据库中所有的现有例句"""
    print("\n⚠️ 警告：这将清空数据库中所有的例句内容（翻译和单词保留），以便重新使用 AI 生成。")
    confirm = input("确认要清空吗？输入 'y' 确认，其他键取消: ").strip().lower()
    
    if confirm == 'y':
        conn = sqlite3.connect('data/study_data.db')
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE vocabulary
                SET example_en = NULL, example_cn = NULL
            """)
            conn.commit()
            print("\n✅ 已成功清空所有旧的例句数据！")
        except Exception as e:
            print(f"\n❌ 清空失败: {e}")
        finally:
            conn.close()
    else:
        print("\n已取消清空操作。")

def add_examples_to_vocabulary(batch_size: int = 50, process_all: bool = False):
    """
    为没有例句的单词添加例句（使用 AI 生成）
    """
    conn = sqlite3.connect('data/study_data.db')
    cur = conn.cursor()

    # 获取没有例句的单词
    query = """
        SELECT id, word, translation, category
        FROM vocabulary
        WHERE (example_en IS NULL OR example_en = '')
    """
    if not process_all:
        query += f" LIMIT {batch_size}"
        
    rows = cur.execute(query).fetchall()

    if not rows:
        print("\n🎉 所有单词都已有例句！没有需要处理的单词。")
        conn.close()
        return

    print(f"\n找到 {len(rows)} 个需要添加例句的单词，正在呼叫 AI 老师...")
    print("=" * 60)

    success_count = 0

    for i, (word_id, word, translation, category) in enumerate(rows, 1):
        print(f"\n[{i}/{len(rows)}] {word} ({translation}) - 语境: {category or '无'}")

        result = generate_example_with_llm(word, translation, category)
        
        if result:
            example_en, example_cn = result
            print(f"  ✅ 英文: {example_en}")
            print(f"  🇨🇳 中文: {example_cn}")
            
            try:
                cur.execute("""
                    UPDATE vocabulary
                    SET example_en = ?, example_cn = ?
                    WHERE id = ?
                """, (example_en, example_cn, word_id))
                conn.commit()
                success_count += 1
            except Exception as e:
                print(f"  ❌ 数据库更新失败: {e}")
        else:
            print("  ⚠️ 生成失败，跳过该词。")
            
        time.sleep(0.5)

    conn.close()

    print("\n" + "=" * 60)
    print(f"完成！成功为 {success_count} 个单词添加了智能例句")
    print("=" * 60)

def check_example_status():
    """检查例句状态"""
    conn = sqlite3.connect('data/study_data.db')
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    with_example = cur.execute("""
        SELECT COUNT(*) FROM vocabulary
        WHERE example_en IS NOT NULL AND example_en != ''
    """).fetchone()[0]

    print("=" * 60)
    print("例句状态统计")
    print("=" * 60)
    print(f"单词总数: {total}")
    print(f"有例句: {with_example} ({with_example/total*100:.1f}%)" if total > 0 else "有例句: 0 (0%)")
    print(f"无例句: {total - with_example} ({(total-with_example)/total*100:.1f}%)" if total > 0 else "无例句: 0 (0%)")
    print("=" * 60)

    conn.close()

if __name__ == "__main__":
    print("🧬 BioAgent 智能例句生成工具 (Powered by DeepSeek)")
    print("=" * 60)

    check_example_status()

    print("\n选择操作:")
    print("1. 清空所有旧例句 (准备重新生成)")
    print("2. 为 50 个单词生成 AI 例句 (安全批次)")
    print("3. 为 100 个单词生成 AI 例句 (中等批次)")
    print("4. 一键处理所有无例句单词 (适合空闲时挂机运行)")
    print("5. 退出")

    choice = input("\n请输入选项 (1-5): ").strip()

    if choice == "1":
        clear_old_examples()
        check_example_status()
    elif choice == "2":
        add_examples_to_vocabulary(batch_size=50)
        check_example_status()
    elif choice == "3":
        add_examples_to_vocabulary(batch_size=100)
        check_example_status()
    elif choice == "4":
        confirm = input("处理所有单词可能需要较长时间，确认继续吗？(y/n): ")
        if confirm.strip().lower() == 'y':
            add_examples_to_vocabulary(process_all=True)
            check_example_status()
        else:
            print("已取消操作。")
    else:
        print("已退出")