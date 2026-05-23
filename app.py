# app.py 
import streamlit as st
import pandas as pd
import json
import uuid
import sys
import os
from datetime import datetime
import re
sys.path.append('.')

# ── 工具模块 ────────────────────────────────────────────────────────────
from utils.rag_chain import load_rag_chain
from utils.study_db import (
    init_db, get_overall_stats, get_daily_stats,
    add_mistake, get_mistakes, update_mistake_review, delete_mistake,
    import_questions_from_json, get_random_questions, get_question_count,
    save_quiz_record, get_quiz_history, get_session_summary, add_quiz_question,
    # 单词学习相关
    import_vocabulary_from_excel, add_vocabulary, get_vocabulary_list,
    get_random_vocabulary, get_vocabulary_categories, update_vocabulary_review,
    save_vocabulary_record, get_vocabulary_stats, get_vocabulary_history,
    delete_vocabulary, get_vocabulary_count
)
from utils.ai_grader import (
    grade_answer, generate_mistake_analysis,
    generate_choice_options, generate_dynamic_question
)
from utils.config import DEEPSEEK_API_KEY, CHROMA_PERSIST_DIR, EMBEDDING_MODEL_NAME

# ════════════════════════════════════════════════════════════════════════
# 0. 初始化
# ════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="BioAgent",
    page_icon="🧬",
    layout="wide"
)

init_db()

@st.cache_resource
def get_cached_chain():
    return load_rag_chain()

# ── 全局样式注入 ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Noto Serif SC', serif; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; padding: 8px 20px; font-weight: 600; font-size: 0.95rem; }
.stat-card { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border: 1px solid #0f3460; border-radius: 12px; padding: 20px; text-align: center; color: #e0e0e0; }
.stat-card .number { font-size: 2.2rem; font-weight: 700; color: #e94560; }
.stat-card .label { font-size: 0.85rem; color: #a0a0b0; margin-top: 4px; }
.mistake-card { border-left: 4px solid #e94560; background: #1a1a2e; border-radius: 0 8px 8px 0; padding: 16px; margin-bottom: 12px; color: #e0e0e0; }
.mistake-card.mastered { border-left-color: #00b894; }
.question-box { background: linear-gradient(135deg, #0f3460, #16213e); border-radius: 12px; padding: 24px; color: #ffffff; font-size: 1.1rem; line-height: 1.8; margin-bottom: 16px; border: 1px solid #0f3460; }
.feedback-correct { background: #00b89420; border: 1px solid #00b894; border-radius: 8px; padding: 16px; color: #00b894; }
.feedback-wrong { background: #e9456020; border: 1px solid #e94560; border-radius: 8px; padding: 16px; color: #e94560; }
.stProgress > div > div > div { background: linear-gradient(90deg, #e94560, #0f3460); }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# 1. 侧边栏：全局统计 + 快捷操作
# ════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🧬 BioAgent")
    st.markdown("---")
    stats = get_overall_stats()

    st.markdown(f"""
    **📊 今日学习概况**
    - 题库总量：**{stats['question_bank_size']}** 题
    - 累计作答：**{stats['total_quiz']}** 次
    - 综合正确率：**{stats['accuracy']:.1f}%**
    
    **📌 错题本**
    - 未掌握：**{stats['unmastered']}** 条
    - 已掌握：**{stats['mastered']}** 条
    - ⏰ 今日待复习：**{stats['due_today']}** 条
    """)

    st.markdown("---")
    if st.button("🔄 同步题库", width="stretch"):
        n = import_questions_from_json()
        if n > 0:
            st.success(f"✅ 新导入 {n} 道题")
        else:
            st.info("题库已是最新")

    with st.expander("✏️ 手动添加错题"):
        mq = st.text_area("题目", key="manual_q", height=80)
        ma = st.text_area("我的答案", key="manual_a", height=60)
        ms = st.text_area("正确答案", key="manual_s", height=80)
        if st.button("➕ 添加到错题本"):
            if mq and ms:
                add_mistake(mq, ma or "（未填写）", ms, source="manual")
                st.success("已添加！")
                st.rerun()
            else:
                st.warning("题目和正确答案不能为空")


# ════════════════════════════════════════════════════════════════════════
# 2. 主区域
# ════════════════════════════════════════════════════════════════════════
tab_chat, tab_quiz, tab_mistakes, tab_review, tab_vocab, tab_eval = st.tabs([
    "💬 知识问答", "🎯 知识闯关", "📕 我的错题本", "🔁 今日复习", "📖 单词学习", "📊 学习报告"
])

# ════════════════════════════════════════════════════════════════════════
# TAB 1：知识问答
# ════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.subheader("📚 RAG 知识问答助手")
    st.caption("基于教材知识库回答，可将问题直接存入错题本")
    qa = get_cached_chain()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_qa" not in st.session_state:
        st.session_state.last_qa = None

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("请输入你的分子生物学问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("正在检索教材知识库..."):
                result = qa({"query": prompt})
                answer = result["result"]
                sources = result["source_documents"]

            st.markdown(answer)
            with st.expander("📖 查看知识库引用原文"):
                for i, doc in enumerate(sources):
                    page = doc.metadata.get("page", "未知")
                    st.caption(f"**引用片段 {i+1}**（来源页码：{page}）")
                    st.text(doc.page_content[:500] + "…")

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.last_qa = {"question": prompt, "answer": answer}

    if st.session_state.last_qa:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption("💡 如果这道题你没有答对，可以将它存入错题本")
        with col2:
            if st.button("📕 存入错题本", key="save_chat_mistake"):
                lqa = st.session_state.last_qa
                add_mistake(
                    question=lqa["question"], my_answer="（对话提问，未填写）",
                    std_answer=lqa["answer"], source="chat"
                )
                st.toast("✅ 已存入错题本！")


# ════════════════════════════════════════════════════════════════════════
# TAB 2：知识闯关 
# ════════════════════════════════════════════════════════════════════════
with tab_quiz:
    st.subheader("🎯 知识闯关模式")

    mode_col, setting_col = st.columns([2, 3])
    with mode_col:
        quiz_mode = st.radio("闯关模式", ["📚 题库练习", "🤖 AI 动态出题", "📕 错题回练"], key="quiz_mode")
    with setting_col:
        n_questions = st.slider("本次题目数量", 3, 20, 5, key="n_questions")
        if quiz_mode == "🤖 AI 动态出题":
            topic_hint = st.text_input(
                "练习知识点（可选）",
                placeholder="例如：DNA复制、细胞信号传导、蛋白质合成",
                key="dynamic_topic_hint"
            )
            answer_mode = st.radio("答题形式", ["✏️ 简答题", "🔘 选择题"], horizontal=True, key="answer_mode")
        else:
            topic_hint = ""
            st.caption("💡 当前模式将自动匹配题库中真实的题型")
            answer_mode = "自动"

    st.divider()

    if "quiz_session" not in st.session_state:
        st.session_state.quiz_session = {
            "active": False, "questions": [], "current_idx": 0,
            "session_id": "", "answers": [], "options_cache": {}
        }
    qs = st.session_state.quiz_session

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        start_btn = st.button("🚀 开始闯关", width="stretch", type="primary")
    with btn_col2:
        reset_btn = st.button("🔄 重置", width="stretch")

    if reset_btn:
        st.session_state.quiz_session = {
            "active": False, "questions": [], "current_idx": 0,
            "session_id": str(uuid.uuid4())[:8], "answers": [], "options_cache": {}
        }
        st.rerun()

    if start_btn:
        with st.spinner("正在准备题目…"):
            if quiz_mode == "📚 题库练习":
                questions = get_random_questions(n=n_questions)
                if not questions:
                    st.error("题库为空，请先在侧边栏点击「同步题库」")
                    st.stop()
            elif quiz_mode == "🤖 AI 动态出题":
                qa_chain = get_cached_chain()
                questions = []
                prog = st.progress(0)
                for i in range(n_questions):
                    q = generate_dynamic_question(qa_chain, topic_hint=topic_hint.strip())
                    if q.get("question"):
                        qid = add_quiz_question(q["question"], q["answer"], topic=q.get("topic") or topic_hint.strip(), difficulty=3, q_type="short")
                        q["id"] = qid
                        q["q_type"] = "choice" if "选择题" in answer_mode else "short"
                        questions.append(q)
                    prog.progress((i + 1) / n_questions)
                prog.empty()
            else:
                raw = get_mistakes(mastered=0)
                if not raw:
                    st.info("🎉 没有未掌握的错题了！")
                    st.stop()
                import random
                sampled = random.sample(raw, min(n_questions, len(raw)))
                questions = [
                    {"id": r["id"], "question": r["question"], "answer": r["std_answer"], 
                     "q_type": r.get("q_type", "short"), "options": r.get("options", None), 
                     "topic": "", "is_mistake_review": True}
                    for r in sampled
                ]

        st.session_state.quiz_session = {
            "active": True, "questions": questions, "current_idx": 0,
            "session_id": str(uuid.uuid4())[:8], "answers": [], "options_cache": {}
        }
        st.rerun()

    if qs["active"] and qs["current_idx"] < len(qs["questions"]):
        q_list = qs["questions"]
        idx = qs["current_idx"]
        total = len(q_list)
        q = q_list[idx]
        # 💡 防重名 Session ID
        q_session = qs["session_id"]

        st.progress((idx) / total, text=f"第 {idx+1} / {total} 题")

        q_type = q.get("q_type", "short")
        q_id = q.get("id", idx)
        type_label = {"short": "简答题", "choice": "选择题", "truefalse": "判断题"}.get(q_type, "简答题")
        
        st.markdown(f"""
        <div class="question-box">
            <strong>第 {idx+1} 题</strong> <span style="font-size: 0.8em; background: #e94560; padding: 2px 8px; border-radius: 4px;">{type_label}</span><br><br>
            {q['question']}
        </div>
        """, unsafe_allow_html=True)

        if "graded" not in qs:
            qs["graded"] = False
            qs["grading_result"] = None
            qs["analysis"] = ""

        # 阶段一：等待作答状态
        if not qs["graded"]:
            user_answer = ""
            db_options = []
            
            if q.get("options"):
                if isinstance(q["options"], str):
                    try: db_options = json.loads(q["options"])
                    except: pass
                elif isinstance(q["options"], list):
                    db_options = q["options"]

            if q_type == "truefalse":
                opts = db_options if db_options else ["对", "错"]
                choice = st.radio("请判断：", opts, key=f"tf_{q_session}_{idx}")
                user_answer = choice
            elif q_type == "choice":
                opts = db_options
                if not opts:
                    if q_id not in qs["options_cache"]:
                        with st.spinner("AI 正在生成选项…"):
                            opts = generate_choice_options(q["question"], q["answer"], topic=q.get("topic", ""))
                        if not opts: opts = []
                        qs["options_cache"][q_id] = opts
                    opts = qs["options_cache"].get(q_id, [])

                if opts:
                    formatted_opts = []
                    letters = ["A", "B", "C", "D", "E", "F"]
                    for i, opt in enumerate(opts):
                        if opt.startswith("A.") or opt.startswith("A、") or opt.startswith("A "):
                            formatted_opts.append(opt)
                        else:
                            formatted_opts.append(f"{letters[i] if i < len(letters) else i}. {opt}")
                    choice = st.radio("请选择答案：", formatted_opts, key=f"choice_{q_session}_{idx}")
                    user_answer = choice.split(". ", 1)[1] if ". " in choice else choice
                else:
                    user_answer = st.text_area("请输入答案：", key=f"short_{q_session}_{idx}", height=120)
            else:
                user_answer = st.text_area("请输入你的答案：", key=f"short_{q_session}_{idx}", height=120)

            submit_col, skip_col = st.columns([2, 1])
            with submit_col:
                submitted = st.button("✅ 提交答案", key=f"submit_{q_session}_{idx}", type="primary", width="stretch")
            with skip_col:
                skipped = st.button("⏭️ 跳过", key=f"skip_{q_session}_{idx}", width="stretch")

            if submitted or skipped:
                final_answer = user_answer if (submitted and str(user_answer).strip()) else "（跳过）"

                with st.spinner("AI 正在评分与生成解析…"):
                    grading = grade_answer(q["question"], q["answer"], final_answer)
                    analysis = ""
                    if not grading["is_correct"] and not q.get("is_mistake_review"):
                        analysis = generate_mistake_analysis(q["question"], q["answer"], final_answer)

                save_quiz_record(
                    question_id=q_id, question=q["question"], my_answer=final_answer, std_answer=q["answer"],
                    is_correct=grading["is_correct"], score=grading["score"],
                    ai_feedback=grading["feedback"], session_id=qs["session_id"]
                )

                if q.get("is_mistake_review"):
                    update_mistake_review(q["id"], mastered=grading["is_correct"])
                elif not grading["is_correct"]:
                    add_mistake(
                        question=q["question"], my_answer=final_answer, std_answer=q["answer"],
                        analysis=analysis, source="quiz", difficulty=q.get("difficulty", 3)
                    )

                qs["grading_result"] = grading
                qs["analysis"] = analysis
                qs["graded"] = True
                st.rerun()

        # 阶段二：显示解析与下一题状态
        else:
            grading = qs["grading_result"]
            analysis = qs["analysis"]
            
            if grading["is_correct"]:
                st.markdown(f"""
                <div class="feedback-correct">
                    ✅ <strong>回答正确！</strong>（得分：{grading['score']:.1f}/10）<br>{grading['feedback']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="feedback-wrong">
                    ❌ <strong>回答有误</strong>（得分：{grading['score']:.1f}/10）<br>{grading['feedback']}
                </div>
                """, unsafe_allow_html=True)
                if grading.get("key_missing"):
                    st.info(f"📌 关键缺失：{grading['key_missing']}")

            with st.expander("📖 查看标准答案"):
                st.markdown(q["answer"])
                if q.get("analysis"): st.markdown(f"**原题解析：**\n{q['analysis']}")

            if not grading["is_correct"] and not q.get("is_mistake_review"):
                with st.expander("🔍 查看 AI 错题深度解析"):
                    st.markdown(analysis)

            if st.button("➡️ 确认并进入下一题", key=f"next_btn_{q_session}_{idx}", type="primary", width="stretch"):
                qs["answers"].append({
                    "question": q["question"], "is_correct": grading["is_correct"], "score": grading["score"]
                })
                qs["current_idx"] += 1
                qs["graded"] = False
                qs["grading_result"] = None
                qs["analysis"] = ""
                st.rerun()

    elif qs["active"] and qs["current_idx"] >= len(qs["questions"]) and qs["questions"]:
        summary = get_session_summary(qs["session_id"])
        st.balloons()
        st.markdown("## 🏁 本轮闯关完成！")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("题目总数", summary.get("total", 0))
        m2.metric("答对题数", summary.get("correct", 0))
        m3.metric("正确率", f"{summary.get('accuracy', 0):.1f}%")
        m4.metric("平均得分", f"{summary.get('avg_score', 0):.1f}/10")
        st.divider()
        st.markdown("### 📋 本轮详情")
        for r in summary.get("records", []):
            status = "✅" if r["is_correct"] else "❌"
            with st.expander(f"{status} {r['question'][:60]}…"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**我的答案**")
                    st.text(r["my_answer"])
                with col_b:
                    st.markdown("**标准答案**")
                    st.text(r["std_answer"])
                st.caption(f"AI 点评：{r['ai_feedback']}  |  得分：{r['score']:.1f}")

        if st.button("🔄 再来一轮", width="stretch", type="primary"):
            st.session_state.quiz_session = {
                "active": False, "questions": [], "current_idx": 0,
                "session_id": str(uuid.uuid4())[:8], "answers": [], "options_cache": {}
            }
            st.rerun()

# ════════════════════════════════════════════════════════════════════════
# TAB 3：错题本管理
# ════════════════════════════════════════════════════════════════════════
with tab_mistakes:
    st.subheader("📕 我的错题本")
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1: filter_status = st.selectbox("状态筛选", ["全部", "未掌握", "已掌握"], key="m_status")
    with f_col2: filter_tag = st.text_input("按标签筛选", placeholder="输入知识点关键词", key="m_tag")
    with f_col3: filter_source = st.selectbox("来源筛选", ["全部", "quiz", "chat", "manual"], key="m_src")

    mastered_val = None if filter_status == "全部" else (1 if filter_status == "已掌握" else 0)
    mistakes = get_mistakes(mastered=mastered_val, tag=filter_tag or None)
    if filter_source != "全部": mistakes = [m for m in mistakes if m["source"] == filter_source]

    st.caption(f"共 **{len(mistakes)}** 条错题")
    st.divider()

    if not mistakes:
        st.info("🎉 暂无符合条件的错题记录！")
    else:
        for m in mistakes:
            is_mastered = m["mastered"] == 1
            card_class = "mistake-card mastered" if is_mastered else "mistake-card"
            status_icon = "✅" if is_mastered else "❌"
            next_review = m.get("next_review", "—")

            with st.expander(f"{status_icon} [{m['source'].upper()}] {m['question'][:70]}… | 复习次数：{m['review_count']} | 下次复习：{next_review}"):
                tab_a, tab_b, tab_c = st.tabs(["📝 题目详情", "🔍 错题解析", "⚙️ 操作"])
                with tab_a:
                    st.markdown(f"**题目：** {m['question']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**我的答案**")
                        st.text(m["my_answer"])
                    with col2:
                        st.markdown("**正确答案**")
                        st.text(m["std_answer"])
                with tab_b:
                    if m.get("analysis"): st.markdown(m["analysis"])
                    else:
                        if st.button("🤖 AI 生成解析", key=f"gen_analysis_{m['id']}"):
                            with st.spinner("生成中…"):
                                analysis = generate_mistake_analysis(m["question"], m["std_answer"], m["my_answer"])
                            import sqlite3
                            from utils.study_db import get_conn
                            conn = get_conn()
                            conn.execute("UPDATE mistakes SET analysis=? WHERE id=?", (analysis, m["id"]))
                            conn.commit()
                            conn.close()
                            st.markdown(analysis)
                with tab_c:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✅ 标记已掌握", key=f"master_{m['id']}"):
                            update_mistake_review(m["id"], mastered=True)
                            st.toast("已标记为掌握！")
                            st.rerun()
                    with c2:
                        if st.button("🔁 重置复习", key=f"reset_{m['id']}"):
                            update_mistake_review(m["id"], mastered=False)
                            st.toast("已重置复习计划")
                            st.rerun()
                    with c3:
                        if st.button("🗑️ 删除", key=f"del_{m['id']}"):
                            delete_mistake(m["id"])
                            st.toast("已删除")
                            st.rerun()

# ════════════════════════════════════════════════════════════════════════
# TAB 4：今日复习
# ════════════════════════════════════════════════════════════════════════
with tab_review:
    st.subheader("🔁 今日待复习错题")
    st.caption("基于艾宾浩斯遗忘曲线，以下题目到了最佳复习时间")

    due_mistakes = get_mistakes(mastered=0, due_today=True)

    if not due_mistakes:
        st.success("🎉 今日复习任务已完成！没有待复习的错题。")
        st.balloons()
    else:
        st.info(f"📌 今日共有 **{len(due_mistakes)}** 条错题待复习")
        st.divider()

        # 💡 防重名 Session ID
        if "review_session_id" not in st.session_state: 
            st.session_state.review_session_id = str(uuid.uuid4())
            
        if "review_idx" not in st.session_state: st.session_state.review_idx = 0
        if "review_list" not in st.session_state: st.session_state.review_list = due_mistakes

        rev_list = st.session_state.review_list
        rev_idx = st.session_state.review_idx
        r_sid = st.session_state.review_session_id

        if rev_idx < len(rev_list):
            m = rev_list[rev_idx]
            st.progress(rev_idx / len(rev_list), text=f"复习进度：{rev_idx+1} / {len(rev_list)}")

            st.markdown(f"""
            <div class="question-box">
                📌 <strong>错题 #{rev_idx+1}</strong><br><br>
                {m['question']}
            </div>
            """, unsafe_allow_html=True)

            show_key = f"show_answer_{r_sid}_{rev_idx}"
            if show_key not in st.session_state: 
                st.session_state[show_key] = False

            if not st.session_state[show_key]:
                user_recall = st.text_area("请先尝试写出答案（回忆练习）：", key=f"recall_{r_sid}_{rev_idx}", height=100)
                if st.button("👁️ 查看标准答案", key=f"reveal_{r_sid}_{rev_idx}"):
                    st.session_state[show_key] = True
                    st.rerun()
            else:
                st.markdown("**✅ 标准答案：**")
                st.info(m["std_answer"])
                if m.get("analysis"):
                    with st.expander("📖 查看错题解析"): st.markdown(m["analysis"])

                st.markdown("**你这次掌握了吗？**")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 掌握了！", key=f"rev_ok_{r_sid}_{rev_idx}", width="stretch", type="primary"):
                        update_mistake_review(m["id"], mastered=True)  
                        st.session_state.review_idx += 1
                        st.session_state[show_key] = False
                        st.rerun()
                with col2:
                    if st.button("❌ 还没掌握", key=f"rev_fail_{r_sid}_{rev_idx}", width="stretch"):
                        update_mistake_review(m["id"], mastered=False)
                        st.session_state.review_idx += 1
                        st.session_state[show_key] = False
                        st.rerun()
        else:
            st.success("🎉 本轮复习完成！")
            if st.button("🔄 重新开始复习", width="stretch"):
                st.session_state.review_idx = 0
                st.session_state.review_list = get_mistakes(mastered=0, due_today=True)
                st.session_state.review_session_id = str(uuid.uuid4()) # 💡 关键：重置 Session ID
                st.rerun()

# ════════════════════════════════════════════════════════════════════════
# TAB 5：单词学习
# ════════════════════════════════════════════════════════════════════════
with tab_vocab:
    st.subheader("📖 英语单词学习")

    # 单词统计概览
    vocab_stats = get_vocabulary_stats()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📚 单词总数", vocab_stats["total_words"])
    col2.metric("✅ 已掌握", vocab_stats["mastered"])
    col3.metric("📝 学习中", vocab_stats["learning"])
    col4.metric("🆕 新单词", vocab_stats["new_words"])
    col5.metric("⏰ 今日待复习", vocab_stats["due_today"])

    st.divider()

    # 子标签页：单词管理、学习模式
    vocab_tab1, vocab_tab2, vocab_tab3, vocab_tab4, vocab_tab5 = st.tabs([
        "📥 单词库管理", "🎴 闪卡背诵", "✍️ 拼写测试", "📝 例句填空", "📊 学习统计"
    ])

    # ─────────────────────────────────────────────────────────────────────
    # 子标签1：单词库管理
    # ─────────────────────────────────────────────────────────────────────
    with vocab_tab1:
        st.markdown("### 📥 导入和管理单词库")

        col_a, col_b = st.columns([2, 1])

        with col_a:
            st.markdown("#### 📤 从Excel导入单词")
            st.caption("Excel格式要求：word(单词), translation(翻译), category(分类), phonetic(音标), example_en(英文例句), example_cn(中文例句), difficulty(难度1-5)")

            uploaded_file = st.file_uploader("选择Excel文件", type=['xlsx', 'xls'], key="vocab_upload")
            if uploaded_file:
                if st.button("🚀 开始导入", type="primary"):
                    temp_path = f"data/temp_vocab_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    try:
                        added = import_vocabulary_from_excel(temp_path)
                        os.remove(temp_path)
                        if added > 0:
                            st.success(f"✅ 成功导入 {added} 个新单词！")
                            st.rerun()
                        else:
                            st.info("所有单词已存在，无新增")
                    except Exception as e:
                        st.error(f"导入失败：{str(e)}")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

        with col_b:
            st.markdown("#### ➕ 手动添加单词")
            with st.form("add_vocab_form"):
                new_word = st.text_input("单词*", key="new_word")
                new_trans = st.text_input("翻译*", key="new_trans")
                new_cat = st.text_input("分类", key="new_cat")
                new_phone = st.text_input("音标", key="new_phone")
                new_ex_en = st.text_area("英文例句", key="new_ex_en", height=60)
                new_ex_cn = st.text_area("中文例句", key="new_ex_cn", height=60)
                new_diff = st.slider("难度", 1, 5, 3, key="new_diff")

                if st.form_submit_button("➕ 添加单词", type="primary"):
                    if new_word and new_trans:
                        result = add_vocabulary(new_word, new_trans, new_cat, new_phone,
                                               new_ex_en, new_ex_cn, new_diff)
                        if result > 0:
                            st.success(f"✅ 已添加单词：{new_word}")
                            st.rerun()
                        else:
                            st.warning("该单词已存在")
                    else:
                        st.error("请填写单词和翻译")

        st.divider()

        st.markdown("### 📋 单词库浏览")

        categories = get_vocabulary_categories()
        col_filter1, col_filter2 = st.columns([1, 1])

        with col_filter1:
            filter_cat = st.selectbox("按分类筛选", ["全部"] + categories, key="filter_cat")

        with col_filter2:
            filter_mastery = st.selectbox("按掌握程度筛选",
                                         ["全部", "新单词(0)", "初学(1)", "熟悉(2)", "掌握(3)", "精通(4)", "完全掌握(5)"],
                                         key="filter_mastery")

        cat_param = None if filter_cat == "全部" else filter_cat
        mastery_param = None
        if filter_mastery != "全部":
            mastery_param = int(filter_mastery.split("(")[1].split(")")[0])

        vocab_list = get_vocabulary_list(category=cat_param, mastery_level=mastery_param, limit=100)

        if vocab_list:
            st.caption(f"共 {len(vocab_list)} 个单词")
            for v in vocab_list:
                with st.expander(f"**{v['word']}** - {v['translation']} {'⭐' * v['mastery_level']}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if v['category']: st.markdown(f"**分类：** {v['category']}")
                        if v['phonetic']: st.markdown(f"**音标：** {v['phonetic']}")
                        if v['example_en']:
                            st.markdown(f"**例句：** {v['example_en']}")
                            if v['example_cn']: st.caption(f"翻译：{v['example_cn']}")
                        st.caption(f"难度：{'⭐' * v['difficulty']} | 复习次数：{v['review_count']} | 下次复习：{v['next_review']}")
                    with col2:
                        if st.button("🗑️ 删除", key=f"del_vocab_{v['id']}"):
                            delete_vocabulary(v['id'])
                            st.success("已删除")
                            st.rerun()
        else:
            st.info("暂无单词，请先导入或添加单词")

    # ─────────────────────────────────────────────────────────────────────
    # 子标签2：闪卡背诵
    # ─────────────────────────────────────────────────────────────────────
    with vocab_tab2:
        st.markdown("### 🎴 闪卡式背诵")
        st.caption("看到单词，回忆释义，点击翻转查看答案")

        if "flashcard_list" not in st.session_state: st.session_state.flashcard_list = []
        if "flashcard_idx" not in st.session_state: st.session_state.flashcard_idx = 0
        if "flashcard_session_id" not in st.session_state: st.session_state.flashcard_session_id = str(uuid.uuid4())

        with st.expander("⚙️ 学习设置", expanded=len(st.session_state.flashcard_list) == 0):
            col1, col2, col3 = st.columns(3)
            with col1: fc_count = st.number_input("单词数量", 5, 50, 10, key="fc_count")
            with col2:
                fc_categories = get_vocabulary_categories()
                fc_cat = st.selectbox("选择分类", ["全部"] + fc_categories, key="fc_cat")
            with col3: fc_diff = st.selectbox("难度", ["全部", "1", "2", "3", "4", "5"], key="fc_diff")

            if st.button("🎲 开始新一轮背诵", type="primary"):
                cat_param = None if fc_cat == "全部" else fc_cat
                diff_param = None if fc_diff == "全部" else int(fc_diff)
                st.session_state.flashcard_list = get_random_vocabulary(fc_count, cat_param, diff_param)
                st.session_state.flashcard_idx = 0
                st.session_state.flashcard_session_id = str(uuid.uuid4())
                st.rerun()

        if st.session_state.flashcard_list:
            idx = st.session_state.flashcard_idx
            total = len(st.session_state.flashcard_list)
            fc_sid = st.session_state.flashcard_session_id

            if idx < total:
                word_data = st.session_state.flashcard_list[idx]

                st.progress((idx + 1) / total, text=f"进度：{idx + 1} / {total}")

                st.markdown(f"""
                <div class="question-box" style="text-align: center; font-size: 2.5rem; padding: 60px;">
                    {word_data['word']}
                </div>
                """, unsafe_allow_html=True)

                show_fc_key = f"show_flashcard_{fc_sid}_{idx}"
                if show_fc_key not in st.session_state: st.session_state[show_fc_key] = False

                if not st.session_state[show_fc_key]:
                    if st.button("🔄 翻转查看释义", key=f"flip_{fc_sid}_{idx}", type="primary", use_container_width=True):
                        st.session_state[show_fc_key] = True
                        st.rerun()
                else:
                    # 💡 提取安全的HTML变量
                    phone_html = f"<p><strong>音标：</strong>{word_data['phonetic']}</p>" if word_data.get('phonetic') else ""
                    ex_en_html = f"<p><strong>例句：</strong>{word_data['example_en']}</p>" if word_data.get('example_en') else ""
                    ex_cn_html = f"<p style='color: #a0a0b0;'>{word_data['example_cn']}</p>" if word_data.get('example_cn') else ""

                    st.markdown(f"""
                    <div class="feedback-correct" style="text-align: center; padding: 30px; margin-top: 20px;">
                        <h3>{word_data['translation']}</h3>
                        {phone_html}
                        {ex_en_html}
                        {ex_cn_html}
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("**你记住了吗？**")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 记住了", key=f"fc_yes_{fc_sid}_{idx}", type="primary", use_container_width=True):
                            update_vocabulary_review(word_data['id'], True)
                            save_vocabulary_record(word_data['id'], word_data['word'], 'flashcard',
                                                   True, "", st.session_state.flashcard_session_id)
                            st.session_state.flashcard_idx += 1
                            st.session_state[show_fc_key] = False
                            st.rerun()
                    with col2:
                        if st.button("❌ 还没记住", key=f"fc_no_{fc_sid}_{idx}", use_container_width=True):
                            update_vocabulary_review(word_data['id'], False)
                            save_vocabulary_record(word_data['id'], word_data['word'], 'flashcard',
                                                   False, "", st.session_state.flashcard_session_id)
                            st.session_state.flashcard_idx += 1
                            st.session_state[show_fc_key] = False
                            st.rerun()
            else:
                st.success("🎉 本轮背诵完成！")
                correct = sum(1 for r in get_vocabulary_history(50)
                             if r['session_id'] == st.session_state.flashcard_session_id and r['is_correct'])
                st.metric("本轮记住", f"{correct}/{total}")

                if st.button("🔄 开始新一轮", type="primary"):
                    st.session_state.flashcard_list = []
                    st.session_state.flashcard_idx = 0
                    st.session_state.flashcard_session_id = str(uuid.uuid4())
                    st.rerun()
        else:
            st.info("👆 请先在上方设置中开始新一轮背诵")

    # ─────────────────────────────────────────────────────────────────────
    # 子标签3：拼写测试
    # ─────────────────────────────────────────────────────────────────────
    with vocab_tab3:
        st.markdown("### ✍️ 拼写测试")
        st.caption("根据中文释义，拼写出正确的英文单词")

        if "spelling_list" not in st.session_state: st.session_state.spelling_list = []
        if "spelling_idx" not in st.session_state: st.session_state.spelling_idx = 0
        if "spelling_session_id" not in st.session_state: st.session_state.spelling_session_id = str(uuid.uuid4())

        with st.expander("⚙️ 测试设置", expanded=len(st.session_state.spelling_list) == 0):
            col1, col2, col3 = st.columns(3)
            with col1: sp_count = st.number_input("单词数量", 5, 50, 10, key="sp_count")
            with col2:
                sp_categories = get_vocabulary_categories()
                sp_cat = st.selectbox("选择分类", ["全部"] + sp_categories, key="sp_cat")
            with col3: sp_diff = st.selectbox("难度", ["全部", "1", "2", "3", "4", "5"], key="sp_diff")

            if st.button("🎯 开始拼写测试", type="primary"):
                cat_param = None if sp_cat == "全部" else sp_cat
                diff_param = None if sp_diff == "全部" else int(sp_diff)
                st.session_state.spelling_list = get_random_vocabulary(sp_count, cat_param, diff_param)
                st.session_state.spelling_idx = 0
                st.session_state.spelling_session_id = str(uuid.uuid4())
                st.rerun()

        if st.session_state.spelling_list:
            idx = st.session_state.spelling_idx
            total = len(st.session_state.spelling_list)
            sp_sid = st.session_state.spelling_session_id

            if idx < total:
                word_data = st.session_state.spelling_list[idx]

                st.progress((idx + 1) / total, text=f"进度：{idx + 1} / {total}")

                hint_html = f"<p style='color: #a0a0b0; margin-top: 10px;'>提示：{word_data['category']}</p>" if word_data.get("category") else ""

                st.markdown(
                    '<div class="question-box">'
                    '<p style="font-size: 1.2rem; margin-bottom: 10px;">请拼写出以下单词：</p>'
                    f'<h2 style="color: #e94560;">{word_data["translation"]}</h2>'
                    f'{hint_html}'
                    '</div>',
                    unsafe_allow_html=True
                )

                submitted_key = f"spelling_submitted_{sp_sid}_{idx}"
                answer_key = f"spelling_answer_{sp_sid}_{idx}"
                saved_key = f"spelling_saved_{sp_sid}_{idx}"

                if submitted_key not in st.session_state:
                    st.session_state[submitted_key] = False

                if not st.session_state[submitted_key]:
                    user_spelling = st.text_input("你的答案", key=f"spelling_input_{sp_sid}_{idx}")
                    if st.button("✅ 提交答案", key=f"submit_spelling_{sp_sid}_{idx}", type="primary"):
                        if user_spelling.strip():
                            st.session_state[answer_key] = user_spelling.strip()
                            st.session_state[submitted_key] = True
                            st.rerun() 
                        else:
                            st.warning("请输入答案")
                else:
                    user_spelling = st.session_state[answer_key]
                    is_correct = user_spelling.lower() == word_data['word'].lower()

                    example_html = f"<p>{word_data['example_en']}</p>" if word_data.get("example_en") else ""

                    if is_correct:
                        st.markdown(
                            f'<div class="feedback-correct">'
                            f'<h3>✅ 正确！</h3>'
                            f'<p><strong>{word_data["word"]}</strong> - {word_data["translation"]}</p>'
                            f'{example_html}'
                            f'</div>', unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="feedback-wrong">'
                            f'<h3>❌ 错误</h3>'
                            f'<p>你的答案：<strong>{user_spelling}</strong></p>'
                            f'<p>正确答案：<strong>{word_data["word"]}</strong> - {word_data["translation"]}</p>'
                            f'{example_html}'
                            f'</div>', unsafe_allow_html=True
                        )

                    if saved_key not in st.session_state:
                        update_vocabulary_review(word_data['id'], is_correct)
                        save_vocabulary_record(word_data['id'], word_data['word'], 'spelling',
                                              is_correct, user_spelling, st.session_state.spelling_session_id)
                        st.session_state[saved_key] = True

                    if st.button("➡️ 下一题", key=f"next_spelling_{sp_sid}_{idx}", type="primary", use_container_width=True):
                        st.session_state.spelling_idx += 1
                        st.rerun()

            else:
                st.success("🎉 拼写测试完成！")
                records = [r for r in get_vocabulary_history(100)
                          if r['session_id'] == st.session_state.spelling_session_id]
                correct = sum(1 for r in records if r['is_correct'])
                st.metric("正确率", f"{correct}/{total} ({correct/total*100:.1f}%)")

                if st.button("🔄 开始新测试", type="primary"):
                    st.session_state.spelling_list = []
                    st.session_state.spelling_idx = 0
                    st.session_state.spelling_session_id = str(uuid.uuid4())
                    st.rerun()
        else:
            st.info("👆 请先在上方设置中开始拼写测试")

    # ─────────────────────────────────────────────────────────────────────
    # 子标签4：例句填空
    # ─────────────────────────────────────────────────────────────────────
    with vocab_tab4:
        st.markdown("### 📝 例句填空")
        st.caption("根据例句上下文，填入正确的单词")

        if "fillblank_list" not in st.session_state: st.session_state.fillblank_list = []
        if "fillblank_idx" not in st.session_state: st.session_state.fillblank_idx = 0
        if "fillblank_session_id" not in st.session_state: st.session_state.fillblank_session_id = str(uuid.uuid4())

        with st.expander("⚙️ 测试设置", expanded=len(st.session_state.fillblank_list) == 0):
            col1, col2, col3 = st.columns(3)
            with col1: fb_count = st.number_input("题目数量", 5, 50, 10, key="fb_count")
            with col2:
                fb_categories = get_vocabulary_categories()
                fb_cat = st.selectbox("选择分类", ["全部"] + fb_categories, key="fb_cat")
            with col3: fb_diff = st.selectbox("难度", ["全部", "1", "2", "3", "4", "5"], key="fb_diff")

            if st.button("📝 开始填空练习", type="primary"):
                cat_param = None if fb_cat == "全部" else fb_cat
                diff_param = None if fb_diff == "全部" else int(fb_diff)
                all_words = get_random_vocabulary(fb_count * 5, cat_param, diff_param)
                words_with_example = [w for w in all_words if w.get('example_en') and w['example_en'].strip()][:fb_count]

                if len(words_with_example) < fb_count:
                    st.warning(f"⚠️ 当前分类只找到 {len(words_with_example)} 个有例句的单词（需要 {fb_count} 个）。建议：")
                    st.info("1. 减少题目数量\n2. 选择'全部'分类\n3. 或先为单词添加例句")
                    if len(words_with_example) == 0:
                        st.error("没有找到任何有例句的单词，无法开始练习")
                    else:
                        st.session_state.fillblank_list = words_with_example
                        st.session_state.fillblank_idx = 0
                        st.session_state.fillblank_session_id = str(uuid.uuid4())
                        st.rerun()
                else:
                    st.session_state.fillblank_list = words_with_example
                    st.session_state.fillblank_idx = 0
                    st.session_state.fillblank_session_id = str(uuid.uuid4())
                    st.rerun()

        if st.session_state.fillblank_list:
            idx = st.session_state.fillblank_idx
            total = len(st.session_state.fillblank_list)
            fb_sid = st.session_state.fillblank_session_id

            if idx < total:
                word_data = st.session_state.fillblank_list[idx]

                st.progress((idx + 1) / total, text=f"进度：{idx + 1} / {total}")

                example = word_data['example_en']
                word_to_blank = word_data['word']
                pattern = re.compile(rf'\b{re.escape(word_to_blank)}\b', re.IGNORECASE)
                blanked_example = pattern.sub("______", example)

                st.markdown(f"""
                <div class="question-box">
                    <p style="font-size: 1.1rem; line-height: 1.8;">
                        {blanked_example}
                    </p>
                    <p style="color: #a0a0b0; margin-top: 15px;">提示：{word_data['translation']}</p>
                </div>
                """, unsafe_allow_html=True)

                submitted_key = f"fillblank_submitted_{fb_sid}_{idx}"
                answer_key = f"fillblank_answer_{fb_sid}_{idx}"
                saved_key = f"fillblank_saved_{fb_sid}_{idx}"

                if submitted_key not in st.session_state:
                    st.session_state[submitted_key] = False

                if not st.session_state[submitted_key]:
                    user_answer = st.text_input("填入单词", key=f"fillblank_input_{fb_sid}_{idx}", placeholder="输入英文单词...")

                    if st.button("✅ 提交答案", key=f"submit_fillblank_{fb_sid}_{idx}", type="primary"):
                        if user_answer.strip():
                            st.session_state[answer_key] = user_answer
                            st.session_state[submitted_key] = True
                            st.rerun()
                        else:
                            st.warning("请输入答案")
                else:
                    user_answer = st.session_state[answer_key]
                    is_correct = user_answer.strip().lower() == word_data['word'].lower()

                    ex_cn_html = f"<p style='color: #a0a0b0;'>{word_data['example_cn']}</p>" if word_data.get('example_cn') else ""

                    if is_correct:
                        # 使用隐式字符串拼接，彻底避开 Markdown 的代码块缩进陷阱
                        st.markdown(
                        '<div class="feedback-correct" style="text-align: center; padding: 30px; margin-top: 20px;">'
                        f'<h3>{word_data["translation"]}</h3>'
                        f'{phone_html}'
                        f'{ex_en_html}'
                        f'{ex_cn_html}'
                        '</div>', 
                        unsafe_allow_html=True
                    )
                    else:
                        st.markdown(f"""
                            <div class="feedback-wrong">
                            <h3>❌ 错误</h3>
                            <p>你的答案：<strong>{user_answer}</strong></p>
                            <p>正确答案：<strong>{word_data['word']}</strong> - {word_data['translation']}</p>
                            <p style="margin-top: 10px;">{word_data['example_en']}</p>
                            {ex_cn_html}
                            </div>
                        """, unsafe_allow_html=True)

                    if saved_key not in st.session_state:
                        update_vocabulary_review(word_data['id'], is_correct)
                        save_vocabulary_record(word_data['id'], word_data['word'], 'fill_blank',
                                              is_correct, user_answer, st.session_state.fillblank_session_id)
                        st.session_state[saved_key] = True

                    if st.button("➡️ 下一题", key=f"next_fillblank_{fb_sid}_{idx}", type="primary", use_container_width=True):
                        st.session_state.fillblank_idx += 1
                        st.rerun()
            else:
                st.success("🎉 填空练习完成！")
                records = [r for r in get_vocabulary_history(100)
                          if r['session_id'] == st.session_state.fillblank_session_id]
                correct = sum(1 for r in records if r['is_correct'])
                st.metric("正确率", f"{correct}/{total} ({correct/total*100:.1f}%)")

                if st.button("🔄 开始新练习", type="primary"):
                    st.session_state.fillblank_list = []
                    st.session_state.fillblank_idx = 0
                    st.session_state.fillblank_session_id = str(uuid.uuid4())
                    st.rerun()
        else:
            st.info("👆 请先在上方设置中开始填空练习")

    # ─────────────────────────────────────────────────────────────────────
    # 子标签5：学习统计
    # ─────────────────────────────────────────────────────────────────────
    with vocab_tab5:
        st.markdown("### 📊 单词学习统计")

        vocab_stats = get_vocabulary_stats()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📚 单词总数", vocab_stats["total_words"])
        col2.metric("✅ 已掌握", vocab_stats["mastered"])
        col3.metric("📝 学习中", vocab_stats["learning"])
        col4.metric("🆕 新单词", vocab_stats["new_words"])

        st.divider()

        col5, col6 = st.columns(2)
        col5.metric("📖 累计练习次数", vocab_stats["total_records"])
        col6.metric("🎯 综合正确率", f"{vocab_stats['accuracy']:.1f}%")

        st.divider()

        st.markdown("#### 📂 分类统计")
        categories = get_vocabulary_categories()
        if categories:
            cat_stats = []
            for cat in categories:
                words = get_vocabulary_list(category=cat)
                mastered = sum(1 for w in words if w['mastery_level'] >= 4)
                cat_stats.append({
                    "分类": cat,
                    "单词数": len(words),
                    "已掌握": mastered,
                    "掌握率": f"{mastered/len(words)*100:.1f}%" if words else "0%"
                })
            df_cat = pd.DataFrame(cat_stats)
            st.dataframe(df_cat, use_container_width=True)
        else:
            st.info("暂无分类数据")

        st.divider()

        st.markdown("#### 📝 最近学习记录")
        history = get_vocabulary_history(30)
        if history:
            df_hist = pd.DataFrame(history)[["created_at", "word", "mode", "is_correct", "user_input"]].copy()
            df_hist.columns = ["时间", "单词", "模式", "正确", "用户输入"]
            df_hist["模式"] = df_hist["模式"].map({
                "flashcard": "🎴 闪卡",
                "spelling": "✍️ 拼写",
                "fill_blank": "📝 填空"
            })
            df_hist["正确"] = df_hist["正确"].map({1: "✅", 0: "❌"})
            st.dataframe(df_hist, use_container_width=True)
        else:
            st.info("暂无学习记录")

# ════════════════════════════════════════════════════════════════════════
# TAB 6：学习报告
# ════════════════════════════════════════════════════════════════════════
with tab_eval:
    st.subheader("📊 学习数据报告")
    stats = get_overall_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("题库总量", stats["question_bank_size"])
    c2.metric("累计作答", stats["total_quiz"])
    c3.metric("综合正确率", f"{stats['accuracy']:.1f}%")
    c4.metric("错题总数", stats["total_mistakes"], delta=f"-{stats['mastered']} 已掌握", delta_color="inverse")
    st.divider()

    daily = get_daily_stats(14)
    if daily:
        df_daily = pd.DataFrame(daily).sort_values("date")
        st.markdown("#### 📈 近14天答题趋势")
        chart_df = df_daily.set_index("date")[["quiz_count", "correct_count"]].copy()
        chart_df.columns = ["作答题数", "答对题数"]
        st.line_chart(chart_df)
        st.markdown("#### 📌 错题本动态")
        mistake_df = df_daily.set_index("date")[["mistake_added", "mistake_reviewed"]].copy()
        mistake_df.columns = ["新增错题", "复习错题"]
        st.bar_chart(mistake_df)
    else:
        st.info("暂无足够的历史数据，开始答题后这里会显示学习趋势图")
    st.divider()

    st.markdown("#### 🔬 RAG Agent 性能评估报告")
    csv_path = "data/evaluation_results.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        avg_baseline = df["Baseline_Score"].mean()
        avg_rag = df["RAG_Score"].mean()
        improvement = ((avg_rag - avg_baseline) / avg_baseline) * 100
        e1, e2, e3 = st.columns(3)
        e1.metric("基础模型平均分", f"{avg_baseline:.2f}/10")
        e2.metric("RAG Agent 平均分", f"{avg_rag:.2f}/10", f"+{improvement:.1f}%")
        e3.metric("测试样本量", f"{len(df)} 题")
        chart_data = df[["Baseline_Score", "RAG_Score"]].copy()
        chart_data.columns = ["原始 DeepSeek", "知识库 RAG"]
        st.line_chart(chart_data)
        with st.expander("🔍 查看详细评估明细"):
            st.dataframe(df)
    else:
        st.warning("⚠️ 未检测到评估数据，请先运行 `python scripts/run_evaluation.py`")

    st.divider()
    st.markdown("#### 🗂️ 最近作答记录")
    history = get_quiz_history(limit=30)
    if history:
        df_hist = pd.DataFrame(history)[["created_at", "question", "is_correct", "score", "ai_feedback"]].copy()
        df_hist.columns = ["时间", "题目", "答对", "得分", "AI点评"]
        df_hist["题目"] = df_hist["题目"].str[:40] + "…"
        df_hist["答对"] = df_hist["答对"].map({1: "✅", 0: "❌"})
        st.dataframe(df_hist)
    else:
        st.info("暂无答题记录")