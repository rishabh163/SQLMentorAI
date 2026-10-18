"""SQLMentor AI - Practice mode.

Flow: the learner enters a name, sees a question and submits SQL.
The evaluator checks the answer, and progress.py saves the result.
"""
import streamlit as st

from src.evaluator import evaluate, load_questions
from src.progress import (
    build_summary,
    current_difficulty,
    load_attempts,
    next_question,
    record_attempt,
    save_attempts,
)

st.set_page_config(page_title="SQLMentor AI", layout="wide")
st.title("SQLMentor AI")
st.caption("Practice SQL with real data problems.")

# Simple messages for the reason codes given by the evaluator
REASONS = {
    "wrong_columns": "The number of columns is different from the task.",
    "wrong_order": "The rows are right, but the order is wrong. Check ORDER BY.",
    "extra_rows": "Your result has extra rows. Check your WHERE condition.",
    "missing_rows": "Your result is missing some rows. Check your WHERE condition.",
    "wrong_values": "Some values are different from the expected result.",
}

questions = load_questions()

# ---------- Sidebar: learner name ----------
learner = st.sidebar.text_input("Your name")
if not learner.strip():
    st.info("Enter your name in the sidebar to start.")
    st.stop()

# ---------- Load this learner's saved answers (only when the name changes) ----------
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

attempts = st.session_state.attempts

# ---------- Pick a question ----------
if st.session_state.question is None:
    level = current_difficulty(attempts)
    st.session_state.question = next_question(questions, attempts, level)
question = st.session_state.question

# ---------- Show the question ----------
if question is None:
    st.success("You have solved every question. Great work!")
else:
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

# ---------- Learning summary ----------
summary = build_summary(attempts)
accuracy = summary["overall_accuracy"]
st.sidebar.metric("Level", summary["level"])
st.sidebar.metric("Overall accuracy", "-" if accuracy is None else f"{accuracy}%")

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