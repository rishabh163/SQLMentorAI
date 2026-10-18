"""Progress tracking for SQLMentor AI.

What this file does:
1. Remembers every answer a learner submits.
2. Finds the score of each SQL module.
3. Chooses the learner's level: Beginner, Intermediate or Advanced.
4. Saves progress in a file, so it is not lost when the app closes.

This file never runs SQL and never checks if an answer is right.
The evaluator does that. We only store its result.
"""
import json
import re
from pathlib import Path

# The five SQL modules of the app
MODULES = [
    "SELECT + WHERE",
    "Aggregate Functions",
    "GROUP BY + HAVING",
    "INNER JOIN + LEFT JOIN",
    "Subqueries",
]
# The four results the evaluator can give
VALID_STATUSES = ("correct", "partial", "incorrect", "error")
# The level changes only after the learner tries this many questions
MIN_QUESTIONS = 3
# Folder where each learner's progress file is saved
PROGRESS_DIR = Path(__file__).resolve().parent.parent / "data" / "progress"


def _progress_path(learner_id):
    """Make the file name from the learner's name.

    We keep only letters, numbers, _ and -, so the file always
    stays inside the data/progress folder.
    """
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", learner_id or "")[:40]
    if not safe:
        raise ValueError("Please enter a learner name.")
    return PROGRESS_DIR / f"{safe}.json"


def load_attempts(learner_id):
    """Read the learner's saved answers.

    If there is no file, or the file is broken, start with an empty list.
    """
    path = _progress_path(learner_id)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def save_attempts(learner_id, attempts):
    """Write the learner's answers to their own file."""
    path = _progress_path(learner_id)
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(attempts, file, indent=2)


def record_attempt(attempts, question, status, hints_used=0):
    """Add one answer to the list.

    The status (correct, partial, incorrect or error) comes from the evaluator.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Unknown status: {status!r}")
    attempts.append({
        "question_id": question["id"],
        "module": question["module"],
        "status": status,
        "hints_used": hints_used,
    })


def topic_progress(attempts):
    """Find the score of each module.

    For every module we count:
    - attempted: how many different questions the learner tried
    - correct: how many of those were solved
    - submissions: how many answers were submitted in total
    - accuracy: percent of tried questions that were solved
    """
    progress = {
        module: {"attempted": 0, "correct": 0, "submissions": 0, "accuracy": 0}
        for module in MODULES
    }

    # A question is counted once. It is solved if at least one try was correct,
    # so a learner who fails first and then fixes the query is not punished.
    results = {}
    for attempt in attempts:
        question_id = attempt["question_id"]
        module = attempt["module"]
        progress[module]["submissions"] += 1

        if question_id not in results:
            results[question_id] = [module, False]
        if attempt["status"] == "correct":
            results[question_id][1] = True

    for module, solved in results.values():
        progress[module]["attempted"] += 1
        progress[module]["correct"] += int(solved)

    for stats in progress.values():
        if stats["attempted"] > 0:
            stats["accuracy"] = round(stats["correct"] / stats["attempted"] * 100)

    return progress


def overall_accuracy(attempts):
    """Percent of tried questions that were solved.

    Returns None if the learner has not tried any question yet.
    """
    progress = topic_progress(attempts)
    attempted = sum(x["attempted"] for x in progress.values())
    correct = sum(x["correct"] for x in progress.values())

    if attempted == 0:
        return None
    return round(correct / attempted * 100)


def current_difficulty(attempts, start="Beginner"):
    """Choose the learner's level from the overall score.

    Below 50   -> Beginner
    50 to 80   -> Intermediate
    Above 80   -> Advanced

    Until the learner tries 3 questions, we keep the starting level.
    """
    progress = topic_progress(attempts)
    attempted = sum(x["attempted"] for x in progress.values())
    if attempted < MIN_QUESTIONS:
        return start

    accuracy = overall_accuracy(attempts)
    if accuracy < 50:
        return "Beginner"
    if accuracy <= 80:
        return "Intermediate"
    return "Advanced"


def next_question(questions, attempts, difficulty):
    """Pick the next question the learner has not solved yet.

    We prefer the learner's current level, and the module with the lowest score.
    """
    # Questions already solved
    solved = set()
    for attempt in attempts:
        if attempt["status"] == "correct":
            solved.add(attempt["question_id"])

    progress = topic_progress(attempts)

    available = [
        q for q in questions
        if q["id"] not in solved and q["difficulty"] == difficulty
    ]
    # If nothing is left at this level, use any unsolved question
    if not available:
        available = [q for q in questions if q["id"] not in solved]
    if not available:
        return None

    return min(available, key=lambda q: progress[q["module"]]["accuracy"])


def build_summary(attempts):
    """Make a short report to show on the screen.

    It has the overall score, the level, strong modules (above 80),
    weak modules (below 50) and what to practise next.
    """
    progress = topic_progress(attempts)

    weak_areas = [
        module for module, stats in progress.items()
        if stats["attempted"] > 0 and stats["accuracy"] < 50
    ]
    strengths = [
        module for module, stats in progress.items()
        if stats["attempted"] > 0 and stats["accuracy"] > 80
    ]
    untried = [
        module for module, stats in progress.items()
        if stats["attempted"] == 0
    ]

    # Weak module first, then a module not tried yet, then a general message
    if weak_areas:
        recommendation = f"Practice {weak_areas[0]} again."
    elif untried:
        recommendation = f"Next, try {untried[0]}."
    else:
        recommendation = "Keep practising to improve your SQL skills."

    return {
        "overall_accuracy": overall_accuracy(attempts),
        "level": current_difficulty(attempts),
        "strengths": strengths,
        "weak_areas": weak_areas,
        "recommendation": recommendation,
        "topic_progress": progress,
    }


if __name__ == "__main__":
    # Quick test. Run from the project folder: python -m src.progress
    from src.evaluator import load_questions  # needed only for this test

    questions = load_questions()
    by_id = {q["id"]: q for q in questions}

    # Four sample answers: q01 wrong then right, q02 partly right, q03 right
    attempts = []
    record_attempt(attempts, by_id["q01"], "incorrect")
    record_attempt(attempts, by_id["q01"], "correct")
    record_attempt(attempts, by_id["q02"], "partial")
    record_attempt(attempts, by_id["q03"], "correct")

    assert overall_accuracy(attempts) == 67          # 2 of 3 questions solved
    assert topic_progress(attempts)["SELECT + WHERE"]["submissions"] == 3
    assert current_difficulty(attempts) == "Intermediate"

    # A new learner with no answers should not crash
    assert overall_accuracy([]) is None
    assert current_difficulty([]) == "Beginner"
    assert build_summary([])["recommendation"] == "Next, try SELECT + WHERE."

    # Check the level rule using 10 fake questions
    def level_at(percent):
        solved = round(percent / 10)                 # how many are correct
        fake = [{"question_id": f"x{i}", "module": "Subqueries",
                 "status": "correct" if i < solved else "incorrect"}
                for i in range(10)]
        return current_difficulty(fake)

    assert level_at(40) == "Beginner"                # below 50
    assert level_at(50) == "Intermediate"            # 50 is included
    assert level_at(80) == "Intermediate"            # 80 is included
    assert level_at(90) == "Advanced"                # above 80

    # A wrong status word must be rejected
    try:
        record_attempt([], by_id["q01"], "maybe")
        raise AssertionError("bad status was accepted")
    except ValueError:
        pass

    # Saving, loading, separate learners and safe file names
    save_attempts("_test_a", attempts)
    assert load_attempts("_test_a") == attempts      # saved data comes back
    assert load_attempts("_test_new") == []          # new learner is empty
    assert _progress_path("../../evil").parent == PROGRESS_DIR  # stays in folder
    _progress_path("_test_a").unlink()               # delete the test file

    print("All progress tests passed.")