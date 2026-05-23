#!/usr/bin/env python3
# import_exam_questions.py
# 将 exam_questions.json 批量导入到 study_data.db 题库
# 使用方式：python import_exam_questions.py
# 可选参数：python import_exam_questions.py --json 你的题目文件.json

import json
import sqlite3
import sys
import os
import argparse

DB_PATH = "data/study_data.db"
DEFAULT_JSON = "exam_questions.json"


def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn


def import_questions(json_path: str, overwrite: bool = False):
    if not os.path.exists(json_path):
        print(f"❌ 找不到文件：{json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    conn = get_conn()
    cur = conn.cursor()

    # 确保表存在
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT NOT NULL,
            answer      TEXT NOT NULL,
            options     TEXT,
            q_type      TEXT DEFAULT 'short',
            topic       TEXT,
            difficulty  INTEGER DEFAULT 3,
            used_count  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    added = 0
    skipped = 0
    updated = 0

    for q in questions:
        question_text = q.get("question", "").strip()
        answer_text = q.get("answer", "").strip()

        if not question_text or not answer_text:
            skipped += 1
            continue

        # 处理 options 字段
        options = q.get("options")
        if isinstance(options, list):
            options = json.dumps(options, ensure_ascii=False)
        elif options == "null" or options == "None":
            options = None

        # 简答题的 explanation 附加到 answer 后
        explanation = q.get("explanation", "")
        if explanation and q.get("q_type") == "short":
            full_answer = answer_text  # 简答题答案已经很完整
        else:
            full_answer = answer_text

        # 检查是否已存在（按题目内容去重）
        existing = cur.execute(
            "SELECT id FROM quiz_questions WHERE question = ?",
            (question_text,)
        ).fetchone()

        if existing:
            if overwrite:
                cur.execute("""
                    UPDATE quiz_questions
                    SET answer=?, options=?, q_type=?, topic=?, difficulty=?
                    WHERE id=?
                """, (full_answer, options,
                      q.get("q_type", "short"),
                      q.get("topic", "分子生物学"),
                      q.get("difficulty", 3),
                      existing[0]))
                updated += 1
            else:
                skipped += 1
            continue

        cur.execute("""
            INSERT INTO quiz_questions (question, answer, options, q_type, topic, difficulty)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            question_text,
            full_answer,
            options,
            q.get("q_type", "short"),
            q.get("topic", "分子生物学"),
            q.get("difficulty", 3),
        ))
        added += 1

    conn.commit()

    # 统计各类型数量
    stats = cur.execute("""
        SELECT q_type, COUNT(*) as cnt
        FROM quiz_questions
        GROUP BY q_type
        ORDER BY cnt DESC
    """).fetchall()

    total = cur.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
    conn.close()

    print("\n" + "="*50)
    print(f"✅ 导入完成！")
    print(f"   新增：{added} 道")
    print(f"   更新：{updated} 道")
    print(f"   跳过（已存在）：{skipped} 道")
    print(f"\n📊 当前题库总量：{total} 道")
    for q_type, cnt in stats:
        type_name = {"choice": "选择题", "truefalse": "判断题",
                     "short": "简答题"}.get(q_type, q_type)
        print(f"   {type_name}：{cnt} 道")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导入题目到学习数据库")
    parser.add_argument("--json", default=DEFAULT_JSON,
                        help=f"题目JSON文件路径（默认：{DEFAULT_JSON}）")
    parser.add_argument("--overwrite", action="store_true",
                        help="对已存在的题目进行覆盖更新")
    args = parser.parse_args()

    print(f"📂 读取题目文件：{args.json}")
    print(f"🗄️  目标数据库：{DB_PATH}")
    import_questions(args.json, overwrite=args.overwrite)
