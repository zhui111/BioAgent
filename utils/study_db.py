# utils/study_db.py
"""
本地学习数据库管理器
- 使用 SQLite 持久化存储，无需额外服务
- 管理错题本、学习记录、知识测验、单词学习四大模块
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd

DB_PATH = "data/study_data.db"


def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # 让查询结果像字典一样访问
    return conn


def init_db():
    """初始化所有数据表（幂等操作，可重复调用）"""
    conn = get_conn()
    cur = conn.cursor()

    # ── 错题本 ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mistakes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT    NOT NULL,
            my_answer   TEXT    NOT NULL,
            std_answer  TEXT    NOT NULL,
            analysis    TEXT,           -- AI 解析
            tags        TEXT,           -- JSON 数组，如 ["细胞分裂", "DNA复制"]
            source      TEXT,           -- "quiz" | "manual" | "chat"
            difficulty  INTEGER DEFAULT 3,  -- 1(易)~5(难)
            review_count INTEGER DEFAULT 0, -- 已复习次数
            next_review  TEXT,          -- ISO 日期，下次复习时间（间隔重复）
            mastered     INTEGER DEFAULT 0, -- 0=未掌握 1=已掌握
            created_at   TEXT DEFAULT (datetime('now','localtime')),
            updated_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── 知识测验题库 ──────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT NOT NULL,
            answer      TEXT NOT NULL,
            options     TEXT,           -- JSON 数组，选择题选项；NULL 表示简答题
            q_type      TEXT DEFAULT 'short',  -- 'choice' | 'short' | 'truefalse'
            topic       TEXT,           -- 知识点标签
            difficulty  INTEGER DEFAULT 3,
            used_count  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── 测验作答记录 ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER REFERENCES quiz_questions(id),
            question    TEXT NOT NULL,
            my_answer   TEXT NOT NULL,
            std_answer  TEXT NOT NULL,
            is_correct  INTEGER NOT NULL,  -- 0/1
            score       REAL,              -- AI 评分 0~10
            ai_feedback TEXT,              -- AI 点评
            session_id  TEXT,              -- 同一次测验用同一个 session_id
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── 学习统计（每日快照）────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date            TEXT PRIMARY KEY,
            quiz_count      INTEGER DEFAULT 0,
            correct_count   INTEGER DEFAULT 0,
            mistake_added   INTEGER DEFAULT 0,
            mistake_reviewed INTEGER DEFAULT 0,
            study_minutes   INTEGER DEFAULT 0
        )
    """)

    # ── 单词库 ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word        TEXT NOT NULL UNIQUE,
            translation TEXT NOT NULL,
            category    TEXT,           -- 分类：自然地理、生物学、医学等
            phonetic    TEXT,           -- 音标
            example_en  TEXT,           -- 英文例句
            example_cn  TEXT,           -- 中文例句翻译
            difficulty  INTEGER DEFAULT 3,  -- 1(易)~5(难)
            mastery_level INTEGER DEFAULT 0, -- 掌握程度 0~5
            review_count INTEGER DEFAULT 0,  -- 复习次数
            next_review  TEXT,          -- 下次复习时间
            created_at   TEXT DEFAULT (datetime('now','localtime')),
            updated_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── 单词学习记录 ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id     INTEGER REFERENCES vocabulary(id),
            word        TEXT NOT NULL,
            mode        TEXT NOT NULL,  -- 'flashcard' | 'spelling' | 'fill_blank'
            is_correct  INTEGER NOT NULL,  -- 0/1
            user_input  TEXT,           -- 用户输入（拼写测试、填空）
            session_id  TEXT,           -- 学习会话ID
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# 错题本 CRUD
# ═══════════════════════════════════════════════════════════════

def add_mistake(question: str, my_answer: str, std_answer: str,
                analysis: str = "", tags: list = None,
                source: str = "quiz", difficulty: int = 3) -> int:
    """添加一条错题，返回新记录 id"""
    conn = get_conn()
    # 计算第一次复习时间（1天后）
    from datetime import timedelta
    next_review = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO mistakes (question, my_answer, std_answer, analysis, tags, source, difficulty, next_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (question, my_answer, std_answer, analysis,
          json.dumps(tags or [], ensure_ascii=False),
          source, difficulty, next_review))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    _bump_daily("mistake_added")
    return row_id


def get_mistakes(mastered: Optional[int] = None, tag: str = None,
                 due_today: bool = False) -> list:
    """查询错题列表，支持按掌握状态、标签、是否到期筛选"""
    conn = get_conn()
    cur = conn.cursor()
    sql = "SELECT * FROM mistakes WHERE 1=1"
    params = []
    if mastered is not None:
        sql += " AND mastered = ?"
        params.append(mastered)
    if tag:
        sql += " AND tags LIKE ?"
        params.append(f'%{tag}%')
    if due_today:
        today = datetime.now().strftime("%Y-%m-%d")
        sql += " AND (next_review <= ? OR next_review IS NULL)"
        params.append(today)
    sql += " ORDER BY created_at DESC"
    rows = cur.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_mistake_review(mistake_id: int, mastered: bool):
    """
    完成一次复习后更新：
    - 增加 review_count
    - 用简化版间隔重复算法计算下次复习时间
    - 若标记掌握则 mastered=1
    """
    from datetime import timedelta
    conn = get_conn()
    cur = conn.cursor()
    row = dict(cur.execute("SELECT * FROM mistakes WHERE id=?", (mistake_id,)).fetchone())
    if mastered:
        count = row["review_count"] + 1
    else:
        count = 0
    # 间隔重复：未掌握明天复习；掌握后按 1→2→4→7→14→30 天递增
    intervals = [1, 2, 4, 7, 14, 30]
    days = intervals[min(count - 1, len(intervals) - 1)] if mastered else 1
    next_review = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    cur.execute("""
        UPDATE mistakes
        SET review_count=?, next_review=?, mastered=?, updated_at=datetime('now','localtime')
        WHERE id=?
    """, (count, next_review, 1 if mastered else 0, mistake_id))
    conn.commit()
    conn.close()
    _bump_daily("mistake_reviewed")


def delete_mistake(mistake_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM mistakes WHERE id=?", (mistake_id,))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# 题库 CRUD
# ═══════════════════════════════════════════════════════════════

def import_questions_from_json(json_path: str = "data/training_data.json"):
    """将 generate_qa_pairs.py 生成的 QA 对批量导入题库（去重）"""
    if not os.path.exists(json_path):
        return 0
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    conn = get_conn()
    cur = conn.cursor()
    added = 0
    for item in items:
        q = item.get("instruction", "")
        a = item.get("output", "")
        if not q or not a:
            continue
        exists = cur.execute("SELECT 1 FROM quiz_questions WHERE question=?", (q,)).fetchone()
        if not exists:
            cur.execute("INSERT INTO quiz_questions (question, answer, q_type) VALUES (?,?,'short')",
                        (q, a))
            added += 1
    conn.commit()
    conn.close()
    return added


def get_random_questions(n: int = 5, q_type: str = None,
                         topic: str = None, difficulty: int = None) -> list:
    """随机抽取题目，支持按类型/知识点/难度筛选"""
    conn = get_conn()
    cur = conn.cursor()
    sql = "SELECT * FROM quiz_questions WHERE 1=1"
    params = []
    if q_type:
        sql += " AND q_type=?"
        params.append(q_type)
    if topic:
        sql += " AND topic LIKE ?"
        params.append(f"%{topic}%")
    if difficulty:
        sql += " AND difficulty=?"
        params.append(difficulty)
    sql += f" ORDER BY RANDOM() LIMIT ?"
    params.append(n)
    rows = cur.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_quiz_question(question: str, answer: str, options: list = None,
                      q_type: str = "short", topic: str = "", difficulty: int = 3) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO quiz_questions (question, answer, options, q_type, topic, difficulty)
        VALUES (?,?,?,?,?,?)
    """, (question, answer,
          json.dumps(options, ensure_ascii=False) if options else None,
          q_type, topic, difficulty))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_question_count() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
    conn.close()
    return n


# ═══════════════════════════════════════════════════════════════
# 测验记录 CRUD
# ═══════════════════════════════════════════════════════════════

def save_quiz_record(question_id: int, question: str, my_answer: str,
                     std_answer: str, is_correct: bool, score: float,
                     ai_feedback: str, session_id: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO quiz_records
        (question_id, question, my_answer, std_answer, is_correct, score, ai_feedback, session_id)
        VALUES (?,?,?,?,?,?,?,?)
    """, (question_id, question, my_answer, std_answer,
          1 if is_correct else 0, score, ai_feedback, session_id))
    # 更新题目使用次数
    conn.execute("UPDATE quiz_questions SET used_count=used_count+1 WHERE id=?", (question_id,))
    conn.commit()
    conn.close()
    _bump_daily("quiz_count")
    if is_correct:
        _bump_daily("correct_count")


def get_quiz_history(limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM quiz_records ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_summary(session_id: str) -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM quiz_records WHERE session_id=?", (session_id,)
    ).fetchall()
    conn.close()
    records = [dict(r) for r in rows]
    if not records:
        return {}
    total = len(records)
    correct = sum(1 for r in records if r["is_correct"])
    avg_score = sum(r["score"] or 0 for r in records) / total
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total * 100,
        "avg_score": avg_score,
        "records": records
    }


# ═══════════════════════════════════════════════════════════════
# 统计
# ═══════════════════════════════════════════════════════════════

def _bump_daily(field: str, delta: int = 1):
    """更新今日统计"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    conn.execute(f"""
        INSERT INTO daily_stats (date, {field}) VALUES (?, ?)
        ON CONFLICT(date) DO UPDATE SET {field} = {field} + ?
    """, (today, delta, delta))
    conn.commit()
    conn.close()


def get_overall_stats() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    total_mistakes = cur.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0]
    mastered = cur.execute("SELECT COUNT(*) FROM mistakes WHERE mastered=1").fetchone()[0]
    due_today = cur.execute(
        "SELECT COUNT(*) FROM mistakes WHERE mastered=0 AND next_review <= date('now','localtime')"
    ).fetchone()[0]
    total_quiz = cur.execute("SELECT COUNT(*) FROM quiz_records").fetchone()[0]
    correct_quiz = cur.execute("SELECT COUNT(*) FROM quiz_records WHERE is_correct=1").fetchone()[0]
    q_count = cur.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
    conn.close()
    accuracy = (correct_quiz / total_quiz * 100) if total_quiz > 0 else 0
    return {
        "total_mistakes": total_mistakes,
        "mastered": mastered,
        "unmastered": total_mistakes - mastered,
        "due_today": due_today,
        "total_quiz": total_quiz,
        "correct_quiz": correct_quiz,
        "accuracy": accuracy,
        "question_bank_size": q_count,
    }


def get_daily_stats(days: int = 14) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (days,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# 单词库管理
# ═══════════════════════════════════════════════════════════════

def import_vocabulary_from_excel(excel_path: str) -> int:
    """
    从Excel导入单词库
    Excel格式要求：
    - word: 单词
    - translation: 翻译
    - category: 分类（可选）
    - phonetic: 音标（可选）
    - example_en: 英文例句（可选）
    - example_cn: 中文例句（可选）
    - difficulty: 难度1-5（可选，默认3）
    """
    if not os.path.exists(excel_path):
        return 0

    df = pd.read_excel(excel_path)
    conn = get_conn()
    cur = conn.cursor()
    added = 0

    for _, row in df.iterrows():
        word = row.get('word', '').strip()
        translation = row.get('translation', '').strip()

        if not word or not translation:
            continue

        # 检查是否已存在
        exists = cur.execute("SELECT 1 FROM vocabulary WHERE word=?", (word,)).fetchone()
        if exists:
            continue

        category = row.get('category', '')
        phonetic = row.get('phonetic', '')
        example_en = row.get('example_en', '')
        example_cn = row.get('example_cn', '')
        difficulty = int(row.get('difficulty', 3))

        # 计算第一次复习时间（1天后）
        next_review = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        cur.execute("""
            INSERT INTO vocabulary
            (word, translation, category, phonetic, example_en, example_cn, difficulty, next_review)
            VALUES (?,?,?,?,?,?,?,?)
        """, (word, translation, category, phonetic, example_en, example_cn, difficulty, next_review))
        added += 1

    conn.commit()
    conn.close()
    return added


def add_vocabulary(word: str, translation: str, category: str = "",
                   phonetic: str = "", example_en: str = "", example_cn: str = "",
                   difficulty: int = 3) -> int:
    """手动添加单个单词"""
    conn = get_conn()
    cur = conn.cursor()

    # 检查是否已存在
    exists = cur.execute("SELECT 1 FROM vocabulary WHERE word=?", (word,)).fetchone()
    if exists:
        conn.close()
        return -1

    next_review = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    cur.execute("""
        INSERT INTO vocabulary
        (word, translation, category, phonetic, example_en, example_cn, difficulty, next_review)
        VALUES (?,?,?,?,?,?,?,?)
    """, (word, translation, category, phonetic, example_en, example_cn, difficulty, next_review))

    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_vocabulary_list(category: str = None, mastery_level: int = None,
                        due_today: bool = False, limit: int = None) -> List[Dict]:
    """查询单词列表，支持按分类、掌握程度、是否到期筛选"""
    conn = get_conn()
    cur = conn.cursor()
    sql = "SELECT * FROM vocabulary WHERE 1=1"
    params = []

    if category:
        sql += " AND category = ?"
        params.append(category)

    if mastery_level is not None:
        sql += " AND mastery_level = ?"
        params.append(mastery_level)

    if due_today:
        today = datetime.now().strftime("%Y-%m-%d")
        sql += " AND (next_review <= ? OR next_review IS NULL)"
        params.append(today)

    sql += " ORDER BY created_at DESC"

    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    rows = cur.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_random_vocabulary(n: int = 10, category: str = None,
                          difficulty: int = None) -> List[Dict]:
    """随机抽取单词，支持按分类、难度筛选"""
    conn = get_conn()
    cur = conn.cursor()
    sql = "SELECT * FROM vocabulary WHERE 1=1"
    params = []

    if category:
        sql += " AND category = ?"
        params.append(category)

    if difficulty:
        sql += " AND difficulty = ?"
        params.append(difficulty)

    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(n)

    rows = cur.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_vocabulary_categories() -> List[str]:
    """获取所有单词分类"""
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT DISTINCT category FROM vocabulary WHERE category IS NOT NULL AND category != '' ORDER BY category"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def update_vocabulary_review(word_id: int, is_correct: bool):
    """
    更新单词复习记录
    - 增加 review_count
    - 根据正确与否调整 mastery_level (0-5)
    - 使用间隔重复算法计算下次复习时间
    """
    conn = get_conn()
    cur = conn.cursor()
    row = dict(cur.execute("SELECT * FROM vocabulary WHERE id=?", (word_id,)).fetchone())

    count = row["review_count"] + 1
    mastery = row["mastery_level"]

    # 根据正确与否调整掌握程度
    if is_correct:
        mastery = min(5, mastery + 1)
    else:
        mastery = max(0, mastery - 1)

    # 间隔重复：根据掌握程度决定复习间隔
    intervals = [1, 2, 4, 7, 14, 30]  # 天数
    days = intervals[min(mastery, len(intervals) - 1)]
    next_review = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    cur.execute("""
        UPDATE vocabulary
        SET review_count=?, mastery_level=?, next_review=?, updated_at=datetime('now','localtime')
        WHERE id=?
    """, (count, mastery, next_review, word_id))

    conn.commit()
    conn.close()


def save_vocabulary_record(word_id: int, word: str, mode: str,
                           is_correct: bool, user_input: str = "",
                           session_id: str = ""):
    """保存单词学习记录"""
    conn = get_conn()
    conn.execute("""
        INSERT INTO vocabulary_records
        (word_id, word, mode, is_correct, user_input, session_id)
        VALUES (?,?,?,?,?,?)
    """, (word_id, word, mode, 1 if is_correct else 0, user_input, session_id))
    conn.commit()
    conn.close()


def get_vocabulary_stats() -> Dict:
    """获取单词学习统计"""
    conn = get_conn()
    cur = conn.cursor()

    total_words = cur.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    mastered = cur.execute("SELECT COUNT(*) FROM vocabulary WHERE mastery_level >= 4").fetchone()[0]
    learning = cur.execute("SELECT COUNT(*) FROM vocabulary WHERE mastery_level BETWEEN 1 AND 3").fetchone()[0]
    new_words = cur.execute("SELECT COUNT(*) FROM vocabulary WHERE mastery_level = 0").fetchone()[0]
    due_today = cur.execute(
        "SELECT COUNT(*) FROM vocabulary WHERE next_review <= date('now','localtime')"
    ).fetchone()[0]

    total_records = cur.execute("SELECT COUNT(*) FROM vocabulary_records").fetchone()[0]
    correct_records = cur.execute("SELECT COUNT(*) FROM vocabulary_records WHERE is_correct=1").fetchone()[0]

    conn.close()

    accuracy = (correct_records / total_records * 100) if total_records > 0 else 0

    return {
        "total_words": total_words,
        "mastered": mastered,
        "learning": learning,
        "new_words": new_words,
        "due_today": due_today,
        "total_records": total_records,
        "correct_records": correct_records,
        "accuracy": accuracy
    }


def get_vocabulary_history(limit: int = 50) -> List[Dict]:
    """获取单词学习历史"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM vocabulary_records ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_vocabulary(word_id: int):
    """删除单词"""
    conn = get_conn()
    conn.execute("DELETE FROM vocabulary WHERE id=?", (word_id,))
    conn.commit()
    conn.close()


def get_vocabulary_count() -> int:
    """获取单词总数"""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    conn.close()
    return n