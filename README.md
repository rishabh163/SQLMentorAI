# SQLMentor AI

An AI-style SQL tutor built as a capstone project (IIT Patna, Project 1: AI Tutor).
It teaches SQL with lessons, practice questions and a quiz, and it tracks each learner's progress.

## Features

- **Learn mode:** 5 short lessons with example queries you can run.
- **Practice mode:** 10 scenario-based questions with hints. Your answer is checked right away.
- **Quiz mode:** one random question per module, no hints, one try, score at the end.
- **Adaptive level:** the app suggests Beginner, Intermediate or Advanced from your accuracy
  (below 50 = Beginner, 50 to 80 = Intermediate, above 80 = Advanced, after 3 questions).
- **Progress saved per learner** in a small JSON file.

## SQL modules covered

1. SELECT + WHERE
2. Aggregate Functions
3. GROUP BY + HAVING
4. INNER JOIN + LEFT JOIN
5. Subqueries

## How answers are checked

SQLite runs both your query and the expected query, and the two results are compared.
The text of your SQL does not matter, only the result.
So different correct ways of writing a query are accepted.
Column names (aliases) and column order are ignored.
Row order is checked only when the question says order matters.
Possible results: correct, partial (for example extra rows), incorrect, or error.
No AI model decides correctness.

## Tech stack

Python, Streamlit, SQLite, Pandas.

## Project structure

    app.py                 Streamlit app (Learn, Practice, Quiz)
    src/database.py        Safe read-only SQLite query runner
    src/evaluator.py       Compares learner result with expected result
    src/progress.py        Saves and reads learner progress
    src/llm_coach.py       Optional, not built yet
    src/charts.py          Optional, not built yet
    data/questions.json    10 practice and quiz questions
    data/lessons.json      5 lessons
    data/progress/         One JSON file per learner (not stored on GitHub)
    requirements.txt       Libraries to install

## Run on your computer (Windows PowerShell)

    git clone https://github.com/rishabh163/SQLMentorAI.git
    cd SQLMentorAI
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    streamlit run app.py

Then open http://localhost:8501 in your browser.

## Live app

[paste the Streamlit Community Cloud link here after deployment]

## Known limits

- On Streamlit Community Cloud, saved files can be lost when the app restarts or sleeps.
  Learner progress may reset. The app will offer a download and upload option for progress.
- Correctness is checked only by the result. A wrong query that gives the same result
  on this small data would be marked correct. Also, "use a subquery" in a question is not enforced.
- Only read queries (SELECT) are allowed.

## Author

[your name], B.Tech CSE, 7th semester.