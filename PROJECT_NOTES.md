# SQLMentor AI — Project Notes

**Status:** Phase 0 complete; folder structure created.

**Goal:** Build and deploy an AI-powered SQL practice tutor for Data Analyst and Data Scientist beginners.

**Deadline:** 25 October 2026.

**Fixed modules:**
1. SELECT + WHERE
2. Aggregate Functions
3. GROUP BY + HAVING
4. INNER JOIN + LEFT JOIN
5. Subqueries

**Database schema:**
- customers(customer_id, name, city)
- orders(order_id, customer_id, product_id, order_date, quantity, amount)
- products(product_id, product_name, category, price)

**Architecture:** SQLite determines query execution and correctness. The LLM only provides hints, error explanations and learning feedback.

**Tech stack:** Python, Streamlit, SQLite, LLM API, Matplotlib and Seaborn.

**Modes:** Learn, Practice and Quiz.

**Current phase:** Project structure and dependency setup.

**Next task:** Implement `src/database.py`, initialize the SQLite database with sample data, and test SELECT queries.

**Constraints:** Free-first tools, small codebase, beginner-friendly explanations, deployable application. Do not add extra SQL modules to the MVP.

**Security:** Never commit API keys or `.streamlit/secrets.toml` to GitHub.