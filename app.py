"""SQLMentor AI - Learn, Practice, Quiz and Ask a Doubt modes.

Learn: read a short lesson, run an example, or ask the AI to explain it differently.
Practice: solve questions with hints. The evaluator checks the answer
and progress.py saves the result.
Quiz: one question from each module, no hints, score at the end.
Ask a Doubt: chat with the AI tutor about SQL.
Backup: download a PDF report, or a backup file of your progress.
"""
import json
import random
from pathlib import Path

import streamlit as st

from src.charts import show_topic_chart
from src.database import run_query
from src.evaluator import evaluate, load_questions
from src.llm_coach import ai_available, explain_lesson, get_doubt_answer, get_hint
from src.progress import (
    MODULES,
    VALID_STATUSES,
    build_summary,
    current_difficulty,
    load_attempts,
    next_question,
    record_attempt,
    save_attempts,
)
from src.report import build_report
from src.ui import (
    MODE_ICONS,
    hero_banner,
    lesson_card,
    load_css,
    question_card,
    score_card,
    section_label,
    sidebar_about,
    sidebar_brand,
    sidebar_label,
    summary_cards,
)

st.set_page_config(page_title="SQLMentor AI", layout="wide")
load_css()
hero_banner()

LESSONS_PATH = Path(__file__).resolve().parent / "data" / "lessons.json"
MAX_CHAT_QUESTIONS = 20   # limit per session, so the API is not used too much
MAX_CHAT_LENGTH = 500     # longest question we accept (characters)

# Simple messages for the reason codes given by the evaluator
REASONS = {
    "wrong_columns": "The number of columns is different from the task.",
    "wrong_order": "The rows are right, but the order is wrong. Check ORDER BY.",
    "extra_rows": "Your result has extra rows. Check your WHERE condition.",
    "missing_rows": "Your result is missing some rows. Check your WHERE condition.",
    "wrong_values": "Some values are different from the expected result.",
}


def load_lessons():
    with open(LESSONS_PATH, encoding="utf-8") as file:
        return json.load(file)


def show_learn():
    """Learn mode: a short lesson, an example, and an AI explanation."""
    lessons = load_lessons()
    names = [lesson["module"] for lesson in lessons]
    chosen = st.selectbox("Choose a module", names)
    lesson = lessons[names.index(chosen)]

    lesson_card(lesson)
    section_label("Example query")
    st.code(lesson["example"], language="sql")

    run_col, explain_col, _ = st.columns([1, 1.6, 3])
    run_clicked = run_col.button("Run example")
    explain_clicked = explain_col.button("🤖 Explain differently")

    if run_clicked:
        result = run_query(lesson["example"])
        if result["ok"]:
            st.dataframe(result["df"], hide_index=True)
        else:
            st.error(result["error"])

    if explain_clicked:
        with st.spinner("Thinking..."):
            answer = explain_lesson(lesson)
        st.session_state.lesson_ai = {"module": lesson["module"], **answer}

    shown = st.session_state.get("lesson_ai")
    if shown and shown["module"] == lesson["module"]:
        label = "AI tutor" if shown["source"] == "ai" else "Note"
        st.info(f"**{label}:** {shown['text']}")


def show_practice(learner, attempts, questions):
    """Practice mode: solve a question, get feedback, save progress."""
    # Pick a question if we do not have one yet
    if st.session_state.question is None:
        level = current_difficulty(attempts)
        st.session_state.question = next_question(questions, attempts, level)
    question = st.session_state.question

    if question is None:
        st.success("You have solved every question. Great work!")
        return

    question_card(question)

    sql = st.text_area("Your SQL query", height=120, key="sql_" + question["id"])

    # The two buttons sit side by side on the left
    col1, col2, _ = st.columns([1, 1, 4])
    submit = col1.button("Submit", type="primary")
    show_hint = col2.button("💡 Show hint")

    if show_hint and st.session_state.hints_shown < len(question["hints"]):
        st.session_state.hints_shown += 1

    if submit:
        if not sql.strip():
            st.warning("Please write a query first.")
        else:
            result = evaluate(sql, question)  # SQLite decides correctness
            record_attempt(attempts, question, result["status"],
                           st.session_state.hints_shown)
            save_attempts(learner, attempts)
            st.session_state.result = result
            if result["status"] != "correct":
                # Ask for a tip once and keep it, so it is not asked again on every click
                with st.spinner("Thinking of a tip..."):
                    st.session_state.tip = get_hint(
                        question, sql, result["status"], result.get("reason"),
                        result.get("error"), st.session_state.hints_shown)
                st.session_state.tip_question = question["id"]

    # Hints used so far
    for hint in question["hints"][: st.session_state.hints_shown]:
        st.info("Hint: " + hint)

    # Result of the last submission
    result = st.session_state.result
    if result:
        if result["status"] == "correct":
            st.success("Correct! Well done.")
            if st.button("Next question →", type="primary"):
                level = current_difficulty(attempts)
                st.session_state.question = next_question(questions, attempts, level)
                st.session_state.hints_shown = 0
                st.session_state.result = None
                st.rerun()
        elif result["status"] == "partial":
            st.warning("Almost there. " + REASONS.get(result["reason"], ""))
        elif result["status"] == "incorrect":
            st.error("Not correct yet. " + REASONS.get(result["reason"], ""))
        else:
            st.error("SQL error: " + str(result["error"]))

        # Tip for this question (never says if the answer is right, SQLite did that)
        tip = st.session_state.get("tip")
        if (result["status"] != "correct" and tip
                and st.session_state.get("tip_question") == question["id"]):
            label = "AI coach" if tip["source"] == "ai" else "Tip"
            st.info(f"**{label}:** {tip['text']}")


def pick_quiz_questions(questions):
    """Choose one random question from each module."""
    picked = []
    for module in MODULES:
        pool = [q for q in questions if q["module"] == module]
        if pool:
            picked.append(random.choice(pool))
    return picked


def show_quiz(learner, attempts, questions):
    """Quiz mode: one question per module, no hints, one try, score at the end."""
    # Before the quiz starts
    if st.session_state.quiz_questions is None:
        st.write("The quiz has one question from each module. "
                 "There are no hints, and each question gets one try.")
        if st.button("Start quiz", type="primary"):
            st.session_state.quiz_questions = pick_quiz_questions(questions)
            st.session_state.quiz_index = 0
            st.session_state.quiz_results = []
            st.rerun()
        return

    quiz = st.session_state.quiz_questions
    index = st.session_state.quiz_index

    # After the last question: show the score and a review of every answer
    if index >= len(quiz):
        results = st.session_state.quiz_results
        score = results.count("correct")
        score_card(score, len(quiz))

        section_label("Review your answers")
        for q, status in zip(quiz, results):
            icon = "✅" if status == "correct" else "❌"
            with st.expander(f"{icon}  {q['module']}"):
                st.write("**Task:** " + q["task"])
                st.write("**Model answer:**")
                st.code(q["expected_sql"], language="sql")
                st.caption("Other queries that give the same result are also correct.")

        if st.button("Take the quiz again", type="primary"):
            st.session_state.quiz_questions = None
            st.rerun()
        return

    # Show the current question
    question = quiz[index]
    st.progress(index / len(quiz))
    question_card(question, title=f"Question {index + 1} of {len(quiz)}: {question['module']}")

    # len(attempts) grows after every submit, so each question gets an empty box
    sql = st.text_area("Your SQL query", height=120, key=f"quiz_sql_{len(attempts)}")

    if st.button("Submit answer", type="primary"):
        if not sql.strip():
            st.warning("Please write a query first.")
        else:
            result = evaluate(sql, question)  # SQLite decides correctness
            record_attempt(attempts, question, result["status"])
            save_attempts(learner, attempts)
            st.session_state.quiz_results.append(result["status"])
            st.session_state.quiz_index += 1
            st.rerun()


def show_doubt():
    """Ask a Doubt mode: a small chat with the AI tutor about SQL."""
    st.write("Ask any SQL question. The tutor explains with small examples and gives hints. "
             "It will not write the full answer to a practice question.")
    if not ai_available():
        st.info("The AI is not connected, so the tutor answers from the lessons.")

    chat = st.session_state.chat
    for message in chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    asked = sum(1 for message in chat if message["role"] == "user")
    if asked >= MAX_CHAT_QUESTIONS:
        st.warning("You reached the question limit for this session.")
        return

    question = st.chat_input("Ask your SQL doubt...")
    if question and question.strip():
        chat.append({"role": "user", "content": question.strip()[:MAX_CHAT_LENGTH]})
        with st.spinner("Thinking..."):
            answer = get_doubt_answer(chat, load_lessons())
        chat.append({"role": "assistant", "content": answer["text"]})
        st.rerun()

    if chat and st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()


def show_summary(summary):
    """Learning summary: three cards, a table and progress bars."""
    st.divider()
    st.subheader("Your learning summary")
    summary_cards(summary["strengths"], summary["weak_areas"], summary["recommendation"])

    rows = [
        {"Module": m, "Solved": f"{s['correct']}/{s['attempted']}",
         "Submissions": s["submissions"], "Accuracy %": s["accuracy"]}
        for m, s in summary["topic_progress"].items()
    ]
    st.dataframe(rows, hide_index=True)

    section_label("Accuracy by module")
    show_topic_chart({m: s["accuracy"] for m, s in summary["topic_progress"].items()})


def read_uploaded_progress(uploaded_file, questions):
    """Read an uploaded progress file.

    Returns (attempts, None) if the file is good,
    or (None, error message) if it is not.
    We check every row, so a wrong file cannot break the app.
    """
    try:
        data = json.load(uploaded_file)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "This is not a valid JSON file."

    if not isinstance(data, list) or len(data) > 5000:
        return None, "This does not look like a progress file."

    known_ids = {q["id"] for q in questions}
    clean = []
    for item in data:
        if (not isinstance(item, dict)
                or item.get("question_id") not in known_ids
                or item.get("module") not in MODULES
                or item.get("status") not in VALID_STATUSES):
            return None, "The file has wrong data. Upload a file downloaded from this app."
        hints = item.get("hints_used", 0)
        clean.append({
            "question_id": item["question_id"],
            "module": item["module"],
            "status": item["status"],
            "hints_used": hints if isinstance(hints, int) else 0,
        })
    return clean, None


def show_backup(learner, attempts, questions, summary):
    """PDF report for reading, and a backup file for restoring progress later.

    On the free cloud, saved files can be lost when the app restarts,
    so the learner keeps a copy of the backup file.
    """
    # 1) Report for reading and submitting
    try:
        pdf_bytes = build_report(learner, summary, attempts)
    except Exception as error:  # for example: fpdf2 is not installed
        pdf_bytes = None
        st.caption(f"PDF report is not available: {error}")
    if pdf_bytes:
        st.download_button(
            "📄 Download report (PDF)",
            data=pdf_bytes,
            file_name="sqlmentor_report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    # 2) Backup for restoring
    st.caption("On the free cloud, saved files can be lost when the app restarts. "
               "Keep the backup file and upload it later to get your progress back.")
    st.download_button(
        "💾 Backup (.json)",
        data=json.dumps(attempts, indent=2),
        file_name="sqlmentor_progress.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded = st.file_uploader("Restore progress (.json)", type="json")
    if uploaded is not None and st.button("Restore from this file"):
        restored, error = read_uploaded_progress(uploaded, questions)
        if error:
            st.error(error)
        else:
            save_attempts(learner, restored)
            st.session_state.attempts = restored
            st.session_state.question = None
            st.session_state.hints_shown = 0
            st.session_state.result = None
            st.session_state.quiz_questions = None
            st.toast("Progress restored.")
            st.rerun()


# ---------- Main page ----------
questions = load_questions()

# Sidebar: name box, then learner name
sidebar_brand()
learner = st.sidebar.text_input("Your name")
if not learner.strip():
    st.info("Enter your name in the sidebar to start.")
    st.stop()

# Load this learner's saved answers (only when the name changes)
if st.session_state.get("learner") != learner:
    try:
        st.session_state.attempts = load_attempts(learner)
    except ValueError as error:
        st.error(str(error))
        st.stop()
    st.session_state.learner = learner
    st.session_state.question = None
    st.session_state.hints_shown = 0
    st.session_state.result = None
    st.session_state.quiz_questions = None
    st.session_state.chat = []

attempts = st.session_state.attempts

sidebar_label("MODES")
mode = st.sidebar.radio(
    "Mode",
    ["Learn", "Practice", "Quiz", "Doubt"],
    format_func=lambda name: MODE_ICONS[name],  # shows an icon, the value stays "Learn" etc.
    label_visibility="collapsed",
)

if mode == "Learn":
    show_learn()
elif mode == "Practice":
    show_practice(learner, attempts, questions)
elif mode == "Quiz":
    show_quiz(learner, attempts, questions)
else:
    show_doubt()

# Summary is built after the mode runs, so it includes the newest answer
summary = build_summary(st.session_state.attempts)
accuracy = summary["overall_accuracy"]
st.sidebar.metric("Level", summary["level"])
st.sidebar.metric("Overall accuracy", "-" if accuracy is None else f"{accuracy}%")

with st.sidebar.expander("📄 Report and backup"):
    show_backup(learner, st.session_state.attempts, questions, summary)

sidebar_about()

if mode == "Practice":
    show_summary(summary)