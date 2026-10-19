"""SQLMentor AI - Learn, Practice and Quiz modes.

Learn: read a short lesson and run an example query.
Practice: solve questions with hints. The evaluator checks the answer
and progress.py saves the result.
Quiz: one question from each module, no hints, score at the end.
"""
import json
import random
from pathlib import Path

import streamlit as st

from src.database import run_query
from src.evaluator import evaluate, load_questions
from src.progress import (
    MODULES,
    build_summary,
    current_difficulty,
    load_attempts,
    next_question,
    record_attempt,
    save_attempts,
)

st.set_page_config(page_title="SQLMentor AI", layout="wide")
st.title("SQLMentor AI")
st.caption("Learn SQL, practice, and test yourself with a quiz.")

LESSONS_PATH = Path(__file__).resolve().parent / "data" / "lessons.json"

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
    """Learn mode: a short lesson and an example that runs on the database."""
    lessons = load_lessons()
    names = [lesson["module"] for lesson in lessons]
    chosen = st.selectbox("Choose a module", names)
    lesson = lessons[names.index(chosen)]

    st.subheader(lesson["module"])
    st.write(lesson["explanation"])
    st.write("**Example:**")
    st.code(lesson["example"], language="sql")

    if st.button("Run example"):
        result = run_query(lesson["example"])
        if result["ok"]:
            st.dataframe(result["df"], hide_index=True)
        else:
            st.error(result["error"])


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

    st.subheader(f"{question['module']} ({question['difficulty']})")
    st.write(question["scenario"])
    st.write("**Task:** " + question["task"])

    sql = st.text_area("Your SQL query", height=120, key="sql_" + question["id"])

    col1, col2 = st.columns(2)
    submit = col1.button("Submit", type="primary")
    show_hint = col2.button("Show hint")

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

    # Hints used so far
    for hint in question["hints"][: st.session_state.hints_shown]:
        st.info("Hint: " + hint)

    # Result of the last submission
    result = st.session_state.result
    if result:
        if result["status"] == "correct":
            st.success("Correct! Well done.")
            if st.button("Next question"):
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

    # After the last question: show the score
    if index >= len(quiz):
        results = st.session_state.quiz_results
        score = results.count("correct")
        st.subheader(f"Quiz score: {score}/{len(quiz)}")
        for q, status in zip(quiz, results):
            st.write(f"- {q['module']}: " + ("Correct" if status == "correct" else "Not correct"))
        if st.button("Take the quiz again"):
            st.session_state.quiz_questions = None
            st.rerun()
        return

    # Show the current question
    question = quiz[index]
    st.progress(index / len(quiz))
    st.subheader(f"Question {index + 1} of {len(quiz)}: {question['module']}")
    st.write(question["scenario"])
    st.write("**Task:** " + question["task"])

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


def show_summary(summary):
    """Learning summary table."""
    st.divider()
    st.subheader("Your learning summary")
    st.write("**Strong modules:** " + (", ".join(summary["strengths"]) or "None yet"))
    st.write("**Weak modules:** " + (", ".join(summary["weak_areas"]) or "None yet"))
    st.write("**Next step:** " + summary["recommendation"])

    rows = [
        {"Module": m, "Solved": f"{s['correct']}/{s['attempted']}",
         "Submissions": s["submissions"], "Accuracy %": s["accuracy"]}
        for m, s in summary["topic_progress"].items()
    ]
    st.dataframe(rows, hide_index=True)


# ---------- Main page ----------
questions = load_questions()

# Sidebar: learner name
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

attempts = st.session_state.attempts

mode = st.sidebar.radio("Mode", ["Learn", "Practice", "Quiz"])

if mode == "Learn":
    show_learn()
elif mode == "Practice":
    show_practice(learner, attempts, questions)
else:
    show_quiz(learner, attempts, questions)

# Summary is built after the mode runs, so it includes the newest answer
summary = build_summary(attempts)
accuracy = summary["overall_accuracy"]
st.sidebar.metric("Level", summary["level"])
st.sidebar.metric("Overall accuracy", "-" if accuracy is None else f"{accuracy}%")

if mode == "Practice":
    show_summary(summary)