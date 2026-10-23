# SQLMentor AI — Project Notes

**Project:** SQLMentor AI  
**Category:** AI Tutor / SQL Learning Application  
**Academic context:** IIT Patna AI Tutor Capstone  
**Repository:** https://github.com/rishabh163/SQLMentorAI  
**Branch:** `master`  
**Author:** Rishabh Gaur  
**Status:** Deployed on Render; AI provider fallback tested locally and on the deployed app.

---

## 1. Problem Statement

SQL beginners often struggle to write correct queries, understand SQL errors, and identify topics that need more practice.

SQLMentor AI provides structured lessons, SQL execution, result-based evaluation, AI coaching, and learner progress tracking in one Streamlit application.

## 2. Target Learners

Aspiring Data Analysts and Data Scientists who want guided SQL practice using a sample relational database.

## 3. Project Objectives

- Teach five essential SQL modules.
- Provide Learn, Practice, and Quiz modes.
- Execute learner queries using SQLite.
- Evaluate answers through application logic.
- Use Gemini and Groq for AI tutoring when available.
- Provide built-in fallback coaching if AI providers fail.
- Track learner progress and recommend difficulty levels.
- Generate learning summaries and available progress reports.

## 4. Fixed Scope: Five SQL Modules

1. SELECT + WHERE
2. Aggregate Functions
3. GROUP BY + HAVING
4. INNER JOIN + LEFT JOIN
5. Subqueries

These five modules define the project's scope.

## 5. Technology Stack

- Python
- Streamlit
- SQLite
- Pandas
- Gemini API
- Groq API
- JSON
- FPDF2, where used for PDF output
- Git and GitHub
- Render for deployment

Both AI providers are accessed through HTTP requests using Python's standard library.

## 6. Application Architecture

### `app.py` — Main application

Provides the interface for lessons, practice, quizzes, AI assistance, progress tracking, and learning summaries.

### `src/database.py` — SQL execution

- Initializes the sample SQLite database when required.
- Executes permitted learner queries.
- Returns query results or execution errors.
- Applies read-only restrictions and a maximum result-row limit of 500.

### `src/evaluator.py` — Answer evaluation

- Executes learner and reference queries.
- Compares query results using application rules.
- Supports outcomes such as correct, partial, incorrect, and error.

**Critical rule:** SQLite executes the SQL, and the application evaluator determines correctness. Neither Gemini nor Groq decides whether an answer is correct.

### `src/llm_coach.py` — AI tutoring

Provider order:

1. Gemini
2. Groq
3. Built-in fallback

Used for hints, explanations, SQL doubt-solving, and learning feedback. The application records the actual response source for provider badges.

### `src/prompts.py` — Prompt templates

Contains instructions and templates for AI explanations, hints, and learning feedback.

### `src/progress.py` — Learner progress

Stores learner progress in local JSON files and calculates rule-based difficulty recommendations.

### Other files

- `src/charts.py` — Progress visualizations.
- `src/report.py` — Report or export functionality.
- `src/ui.py` — Reusable UI components.
- `data/lessons.json` — Lesson content and examples.
- `data/questions.json` — Predefined practice and quiz questions.
- `assets/style.css` — Application styling.

## 7. Sample Database Schema

**`customers`**
- `customer_id`
- `name`
- `city`

**`products`**
- `product_id`
- `product_name`
- `category`
- `price`

**`orders`**
- `order_id`
- `customer_id`
- `product_id`
- `order_date`
- `quantity`
- `amount`

These tables support filtering, aggregation, grouping, joins, and subqueries.

## 8. Learner Personalization

The application supports learner profiles, progress tracking, and rule-based difficulty recommendations.

Current accuracy rules:

- Below 50%: Beginner
- 50% through 80%: Intermediate
- Above 80%: Advanced

The recommendation uses recorded performance after the configured minimum number of questions has been attempted. It is rule-based, not a trained machine-learning model.

## 9. Question Bank and Evaluation

Questions are loaded from `data/questions.json`.

The evaluator compares learner results with reference results rather than asking an LLM to judge correctness.

**Known limitation:** Different SQL queries can return the same results on a small dataset. Matching output does not always prove that a learner used the exact technique requested.

Dynamic question generation is not part of the current implementation.

## 10. AI Providers and Configuration

### Provider sequence

| Priority | Provider | Purpose |
|---|---|---|
| 1 | Gemini | AI hints, explanations, and coaching |
| 2 | Groq | Alternative AI provider when Gemini fails |
| 3 | Built-in fallback | Basic assistance when both providers fail |

Gemini returned HTTP 429 quota errors during the latest test. Groq successfully answered consecutive SQL questions after the chat-history payload was corrected.

Gemini availability may change depending on quota, rate limits, account access, and provider service status.

### API configuration

The application reads API keys from environment variables or Streamlit secrets.

For local development, create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "YOUR_SUPPORTED_GEMINI_MODEL"
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
GROQ_MODEL = "YOUR_SUPPORTED_GROQ_MODEL"
```

Use valid model identifiers supported by your API accounts. The model settings are configurable.

For Render, configure the required keys and any model overrides in the service's environment-variable settings.

**Security requirements**

- Never commit API keys or `secrets.toml`.
- Never print credentials in logs or screenshots.
- Keep learner progress and generated database files out of version control.
- Do not send the expected SQL answer to the AI for correctness evaluation.

## 11. Progress Storage and Deployment

**Live application:** https://sqlmentorai.onrender.com

The deployed application has been tested, including consecutive AI tutoring questions using Groq.

Learner progress is stored in local JSON files. This is suitable for the lightweight prototype, but Render's default filesystem may be ephemeral. Progress may be lost after a restart or redeployment.

Durable cloud storage is not implemented as part of the current MVP.

## 12. Testing Checklist

### Verified so far

- [x] Python syntax check passed for `src/llm_coach.py`.
- [x] Local Streamlit application starts.
- [x] Consecutive AI doubt questions were answered using Groq.
- [x] Provider fallback was exercised when Gemini returned HTTP 429.
- [x] The deployed Render application was reported working.

### Final regression checks

- [ ] Verify all five SQL modules.
- [ ] Verify Learn, Practice, and Quiz modes.
- [ ] Test correct, incorrect, and invalid SQL submissions.
- [ ] Confirm SQLite evaluation determines correctness.
- [ ] Verify read-only restrictions and the row limit.
- [ ] Test fallback behavior when both AI providers fail.
- [ ] Verify learner profiles, progress, and summaries.
- [ ] Verify available report/export functions.
- [ ] Confirm secrets and private learner data are not committed.

Mark remaining checks complete only after testing them.

## 13. Known Limitations

1. Questions come from a predefined JSON bank.
2. Dynamic AI-generated question creation is not implemented.
3. Progress uses local JSON files rather than durable cloud storage.
4. Result-based evaluation cannot guarantee that every query follows the exact requested technique.
5. AI-generated coaching depends on provider availability and quotas.
6. Built-in fallback provides basic assistance but is less flexible than an LLM.
7. Cloud persistence and the complete final regression checklist require independent verification.

## 14. Future Enhancements

These are proposed improvements, not current features:

- **Dynamic question generation:** Generate and validate questions by module and difficulty.
- **Persistent cloud storage:** Consider PostgreSQL or Supabase if durable multi-user progress becomes necessary.
- **Stronger query evaluation:** Add more test cases and checks for requested SQL techniques.
- **Improved personalization:** Use module-wise accuracy and recurring mistakes.
- **Enhanced analytics:** Improve learner progress visualizations and reporting.

## 15. Final Project Principle

SQLMentor AI uses AI to support learning, not replace reliable programmatic evaluation.

- SQLite executes SQL.
- The evaluator compares results.
- Gemini and Groq provide coaching.
- Built-in fallback helps when AI services are unavailable.
- JSON stores local learner progress.
- The learner remains responsible for writing and understanding SQL queries.
