
# SQLMentor AI

**An AI-Powered SQL Practice Environment for Aspiring Data Analysts and Data Scientists**

SQLMentor AI is a focused SQL learning application developed as an IIT Patna AI Tutor capstone project. It combines structured lessons, SQL practice, quizzes, AI-powered coaching, and learner progress tracking in a Streamlit web application.

The application is designed to help SQL beginners learn by writing and executing queries, receiving feedback, and reviewing their performance.

## Project Objectives

- Provide a structured path for learning essential SQL concepts.
- Let learners practise SQL against a sample relational database.
- Evaluate submitted SQL queries using SQLite rather than an LLM's judgment.
- Use Gemini for hints, explanations, and learning support.
- Track learner progress and adapt the suggested difficulty level.

## Features

### 1. Learn Mode
- Five focused SQL lessons with example queries.
- Run example queries against the SQLite database.
- Request AI explanations in a different style.
- View explanation history during the current application session.

### 2. Practice Mode
- Scenario-based SQL exercises from a predefined question bank.
- Task descriptions identify relevant tables and columns.
- Execute SQL and compare the result with the reference answer.
- Receive feedback and hints to help diagnose mistakes.

### 3. Quiz Mode
- Quiz questions selected from the available question bank.
- Assessment without the normal practice hints.
- Score and progress feedback.

### 4. Personalized Learning
- Learner profiles and progress tracking.
- Beginner, Intermediate, and Advanced difficulty levels.
- Rule-based level recommendations based on recorded accuracy.
- Learning summaries and progress visualizations.

### 5. AI SQL Coach
- Gemini-powered explanations, hints, and coaching.
- Fallback feedback when AI assistance is unavailable.
- AI-generated coaching does not determine SQL correctness.

### 6. SQL Query Evaluation and Safety
- SQLite executes submitted SQL queries.
- Learner results are compared with reference-query results.
- Read-only query restrictions help protect the sample database.
- Query execution is limited to a maximum of 500 returned rows.

## The Five SQL Modules

The project scope is intentionally limited to these five modules:

1. **SELECT + WHERE**
2. **Aggregate Functions**
3. **GROUP BY + HAVING**
4. **INNER JOIN + LEFT JOIN**
5. **Subqueries**

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Streamlit | Web interface |
| SQLite | SQL execution and reference-result evaluation |
| Pandas | Tabular query results and data handling |
| Gemini API | Explanations, hints, and coaching |
| JSON | Question bank, lesson content, and local learner progress |
| FPDF2 | PDF generation, where used by the application |
| Git and GitHub | Version control and source-code hosting |

## How SQL Answers Are Evaluated

The evaluator uses SQLite results to assess submitted SQL queries. It executes the learner's query and the reference query, then compares their results according to the question's evaluation settings.

- Correctness is determined by the application evaluator, not by Gemini.
- Column aliases and column order are ignored where supported by the evaluator.
- Row order is checked when the question requires it.
- Results can be classified as correct, partial, incorrect, or an execution error.

**Known evaluation limitation:** Two different queries can return the same result on a small sample dataset. Result-based comparison cannot always prove that a query follows every instruction in the question. For example, using a subquery is not guaranteed solely by matching the output.

## Database Design

The application creates its SQLite sample database in code when it is missing.

### Tables

- `customers(customer_id, name, city)`
- `products(product_id, product_name, category, price)`
- `orders(order_id, customer_id, product_id, order_date, quantity, amount)`

The generated SQLite database is local application data and should not be committed to GitHub.

### Learner Progress

Learner progress is stored in local JSON files. This is a lightweight approach suitable for the current prototype.

Local files on a cloud host may not survive restarts, redeployments, or instance replacement. Persistent cloud storage is not part of the current implementation.

## Project Structure

```text
SQLMentorAI/
├── app.py
├── requirements.txt
├── README.md
├── PROJECT_NOTES.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── assets/
│   └── style.css
├── data/
│   ├── questions.json
│   └── lessons.json
└── src/
    ├── database.py
    ├── evaluator.py
    ├── llm_coach.py
    ├── progress.py
    ├── charts.py
    ├── prompts.py
    ├── report.py
    └── ui.py
```

The `data/progress/` directory and generated SQLite database are created or used at runtime and may not be present in a fresh Git clone.

## Run Locally on Windows

### Prerequisites
- Python
- Git
- A Gemini API key for AI coaching (optional because fallback feedback is available)

### Setup

```powershell
git clone https://github.com/rishabh163/SQLMentorAI.git
cd SQLMentorAI

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

python -m streamlit run app.py
```

Open the local URL printed in the terminal, normally:

`http://localhost:8501`

### Configure Gemini

Create `.streamlit/secrets.toml` locally:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "YOUR_SUPPORTED_GEMINI_MODEL"
```

Replace the placeholder values with your own valid credentials and model identifier. The model must be supported by your Gemini API access and the application's request format.

Never commit this file or publish your API key. The application should remain usable with fallback coaching when AI access is unavailable.

## Deployment

The application can be deployed as a Python web service on Render, subject to the platform's current service availability and plan limits.

1. Push the project to GitHub.
2. Create a new Web Service in Render and connect the repository.
3. Use the following build command:

   `pip install -r requirements.txt`

4. Use the following start command:

   `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`

5. Add `GEMINI_API_KEY` and `GEMINI_MODEL` through the service's environment-variable settings.
6. Deploy and test all application modes using the public URL.

**Live application:** Add the verified Render URL here after deployment succeeds.

### Deployment limitation

The current learner-progress implementation writes local JSON files. Render's default filesystem is ephemeral, so progress may be lost after a restart or redeployment. Do not promise durable cloud progress until persistent storage has been implemented and tested.

## Testing

The developer has reported that the project's current tests pass. Before submission, perform a final manual regression test on the deployed application:

- Open each of the five modules.
- Test Learn, Practice, and Quiz modes.
- Submit correct, incorrect, and invalid SQL queries.
- Verify that SQLite evaluation—not an AI response—determines correctness.
- Test AI coaching and fallback behavior.
- Verify learner progress, summary, and export functions available in the interface.
- Confirm that secrets and private progress data are not exposed in the repository.

## Limitations

- Practice and quiz questions come from a predefined question bank.
- Dynamic AI-generated question creation is not yet implemented.
- Learner progress currently uses local JSON storage rather than a cloud database.
- Output-based evaluation has limitations when different queries produce identical results.
- AI coaching depends on API access; fallback behavior provides basic assistance when it is unavailable.

## Future Enhancements

These are proposed improvements, not features claimed as implemented:

1. **Dynamic Question Generation:** Generate new questions according to module, difficulty, and learner performance. Validate generated reference SQL before presenting a question, and retain SQLite as the correctness authority.
2. **Persistent Cloud Storage:** Consider PostgreSQL or Supabase if durable multi-user progress and cloud-based learner accounts become necessary.
3. **Improved Evaluation:** Add more test cases and stronger checks for whether a query satisfies the question's requirements.
4. **Enhanced Personalization:** Use module-wise performance and recurring mistakes to refine practice recommendations.
5. **Expanded Analytics:** Improve learner progress visualizations and reporting.

## Author

**Rishabh Gaur**  
B.Tech Computer Science and Engineering, 7th Semester

## Repository

https://github.com/rishabh163/SQLMentorAI
