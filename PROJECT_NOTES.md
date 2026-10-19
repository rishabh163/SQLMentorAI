# SQLMentor AI - Project Notes


**Repo:** https://github.com/rishabh163/SQLMentorAI (branch master)

## Goal

A SQL practice tutor for Data Analyst and Data Scientist beginners.
The learner reads a lesson, solves scenario-based questions, and takes a quiz.
The app tracks progress and suggests the next level.

## Fixed SQL modules

1. SELECT + WHERE
2. Aggregate Functions
3. GROUP BY + HAVING
4. INNER JOIN + LEFT JOIN
5. Subqueries

## Database (SQLite, created by code on first run)

- customers(customer_id, name, city)
- orders(order_id, customer_id, product_id, order_date, quantity, amount)
- products(product_id, product_name, category, price)

The file data/sqlmentor.db is not stored on GitHub. src/database.py builds it
with sample data if it is missing, so a fresh clone or cloud app still works.

## Main design choice

SQLite decides if an answer is correct. It runs the learner's query and the
expected query, then the two results are compared. An AI model never decides
correctness. Column names and column order are ignored. Row order is checked
only when a question says order matters.

## What is built

- src/database.py: safe read-only query runner
- src/evaluator.py: compares results (correct / partial / incorrect / error)
- src/progress.py: one JSON file per learner in data/progress/
- app.py: Learn, Practice and Quiz modes
- data/questions.json (10 questions), data/lessons.json (5 lessons)

## Adaptive level rule

After 3 questions: accuracy below 50 = Beginner, 50 to 80 = Intermediate,
above 80 = Advanced.

## Not built yet (optional)

- src/llm_coach.py: hints with a no-API fallback. It will never judge correctness.
- src/charts.py: progress charts
- assets/style.css: custom styles
- Progress download and upload (planned, because cloud files can reset)

## Known limits

- On Streamlit Community Cloud, saved files can be lost on restart.
- Correctness is checked only by the result, not by how the query is written.
- Only SELECT queries are allowed.

## Security

Never commit API keys, passwords or .streamlit/secrets.toml to GitHub.

## Status (19 Oct 2026)

Core app is working locally and pushed to GitHub.
Next: deploy to Streamlit Community Cloud, then add progress download and upload.