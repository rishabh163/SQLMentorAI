# SQLMentor AI

**An AI-Powered SQL Practice Environment for Aspiring Data Analysts and Data Scientists**

SQLMentor AI is a Streamlit-based SQL learning application developed as an IIT Patna AI Tutor capstone project.

It combines structured lessons, SQL practice, quizzes, AI-powered coaching, and learner progress tracking.

**Live application:** [https://sqlmentorai.onrender.com](https://sqlmentorai.onrender.com)
**GitHub repository:** [https://github.com/rishabh163/SQLMentorAI](https://github.com/rishabh163/SQLMentorAI)

## Features

### 1. Learn Mode

- Five focused SQL modules with examples.
- Execute example queries using SQLite.
- Request AI explanations in a different style.
- View explanation history during the current session.

### 2. Practice Mode

- Scenario-based questions from a predefined question bank.
- Execute SQL against the sample database.
- Compare query results with reference results.
- Receive feedback and hints to help diagnose mistakes.

### 3. Quiz Mode

- Answer questions from the available question bank.
- Practise without normal practice-mode hints.
- Review scores and progress feedback.

### 4. Personalized Learning

- Learner profiles and progress tracking.
- Beginner, Intermediate, and Advanced recommendations.
- Rule-based difficulty adaptation based on recorded accuracy.
- Learning summaries and progress visualizations.

### 5. AI SQL Coach

The application tries providers in this order:

1. **Gemini**
2. **Groq**
3. **Built-in fallback**

AI assistance supports explanations, hints, SQL doubts, and learning feedback. Provider badges indicate the source of the response.

AI provider availability depends on API quotas, rate limits, and service status. Built-in fallback provides basic assistance when both providers fail.

### 6. SQL Execution and Evaluation

- SQLite executes learner queries.
- The application compares learner results with reference results.
- Read-only restrictions help protect the sample database.
- Query execution is limited to a maximum of 500 returned rows.

**Important:** SQL correctness is determined by SQLite execution and application evaluation—not by Gemini or Groq.

## The Five SQL Modules

The project scope is intentionally limited to:

1. **SELECT + WHERE**
2. **Aggregate Functions**
3. **GROUP BY + HAVING**
4. **INNER JOIN + LEFT JOIN**
5. **Subqueries**

## Technology Stack

| Technology     | Purpose                                |
| -------------- | -------------------------------------- |
| Python         | Application logic                      |
| Streamlit      | Web interface                          |
| SQLite         | SQL execution and reference results    |
| Pandas         | Tabular results and data handling      |
| Gemini API     | AI coaching                            |
| Groq API       | Alternative AI coaching provider       |
| JSON           | Lessons, questions, and local progress |
| FPDF2          | PDF generation, where used             |
| Git and GitHub | Version control                        |
| Render         | Deployment                             |

## How SQL Answers Are Evaluated

The application executes the learner's SQL query and a reference query, then compares their results according to the evaluation rules.

- Correctness is not decided by an LLM.
- Column aliases and column order are ignored where supported by the evaluator.
- Row ordering is checked when required by the question.
- Results can be classified as correct, partial, incorrect, or an execution error.

**Known limitation:** Different queries may produce identical results on a small dataset. Result-based comparison cannot always prove that the learner followed every requested SQL technique.

## Sample Database

The application creates its SQLite sample database when it is missing.

### Tables

- `customers(customer_id, name, city)`
- `products(product_id, product_name, category, price)`
- `orders(order_id, customer_id, product_id, order_date, quantity, amount)`

The generated database is runtime data and should not be committed to GitHub.

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

The `data/progress/` directory and generated SQLite database are used at runtime and may not appear in a fresh Git clone.

## Run Locally on Windows

### Prerequisites

- Python
- Git
- API keys for Gemini and/or Groq (optional; built-in fallback is available)

### 1. Clone the repository

```powershell
git clone https://github.com/rishabh163/SQLMentorAI.git
cd SQLMentorAI
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start the application

```powershell
python -m streamlit run app.py
```

Open the local URL printed in the terminal, normally:

[http://localhost:8501](http://localhost:8501)

## Configure AI Providers

Create `.streamlit/secrets.toml` locally if you want to use API-based coaching:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "YOUR_SUPPORTED_GEMINI_MODEL"
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
GROQ_MODEL = "YOUR_SUPPORTED_GROQ_MODEL"
```

Replace the placeholders with your own API credentials and supported model identifiers.

- Gemini is attempted first.
- Groq is attempted if Gemini fails.
- Built-in fallback is used if neither provider succeeds.
- API keys can also be supplied through environment variables.
- The model settings are configurable.

**Never commit `.streamlit/secrets.toml` or publish API keys.**

## Deployment on Render

The application is deployed at:

[https://sqlmentorai.onrender.com](https://sqlmentorai.onrender.com)

For a new deployment:

1. Push the repository to GitHub.

2. Create a Web Service in Render and connect the repository.

3. Set the build command:

   ```bash
   pip install -r requirements.txt
   ```

4. Set the start command:

   ```bash
   streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
   ```

5. Configure API keys and optional model overrides through Render's environment-variable settings.

6. Deploy and test the public application.

### Deployment limitation

Learner progress currently uses local JSON files. Render's default filesystem may be ephemeral, so progress can be lost after restarts or redeployments. Durable cloud storage has not been implemented.

## Testing Checklist

- [ ] Open all five SQL modules.
- [ ] Test Learn, Practice, and Quiz modes.
- [ ] Submit correct, incorrect, and invalid SQL queries.
- [ ] Confirm SQLite evaluation—not AI output—determines correctness.
- [ ] Test AI coaching with an available provider.
- [ ] Test built-in fallback when AI services fail.
- [ ] Verify learner progress and learning summaries.
- [ ] Test available report/export functions.
- [ ] Confirm secrets and private learner data are not committed.

## Known Limitations

- Practice and quiz questions come from a predefined question bank.
- Dynamic AI-generated question creation is not implemented.
- Learner progress uses local JSON storage rather than a persistent cloud database.
- Result-based evaluation has limitations when different queries return identical results.
- AI coaching depends on API access, quotas, and provider availability.

## Future Enhancements

These are proposed improvements, not features currently claimed as implemented:

1. **Dynamic question generation:** Generate and validate exercises by module and difficulty.
2. **Persistent cloud storage:** Consider PostgreSQL or Supabase for durable learner progress.
3. **Stronger evaluation:** Add test cases and checks for requested SQL techniques.
4. **Improved personalization:** Use module-level performance and recurring errors.
5. **Enhanced analytics:** Expand progress charts and learner reports.

## Author

**Rishabh Gaur**

## Repository

[https://github.com/rishabh163/SQLMentorAI](https://github.com/rishabh163/SQLMentorAI)
