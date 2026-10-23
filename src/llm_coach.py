"""AI helper for SQLMentor AI.

Rules:
- The AI only helps (hints, doubts, explanations). SQLite decides if an answer is correct.
- The expected answer is never sent to the AI.
- Without an API key, or if the internet fails, simple built-in help is used.
- Two providers are supported: Gemini (free tier in Google AI Studio) and Claude.
  Put ONE key in .streamlit/secrets.toml or in an environment variable. Never in the code.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from src.prompts import FEEDBACK_TEMPLATE, HINT_TEMPLATE, LESSON_TEMPLATE, TUTOR_SYSTEM

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL = "gemini-3.6-flash"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-haiku-5-5"

# Short help for each reason code from evaluator.py
REASON_HINTS = {
    "sql_error": "Your query has an error. Check spelling, commas and table names.",
    "wrong_columns": "The number of columns is not right. Read the task again.",
    "wrong_values": "The values are different. Check your WHERE or JOIN condition.",
    "extra_rows": "You have extra rows. Do you need a filter?",
    "missing_rows": "Some rows are missing. Is your filter too strict?",
    "wrong_order": "The rows are right, but the order is not. Think about ORDER BY.",
}

# Simple words that point to a lesson (used when the AI is not available)
LESSON_WORDS = {
    "SELECT + WHERE": ["select", "where", "filter", "column", "condition", "rows"],
    "Aggregate Functions": ["count", "sum", "avg", "average", "min", "max", "total", "aggregate"],
    "GROUP BY + HAVING": ["group", "having", "each", "per"],
    "INNER JOIN + LEFT JOIN": ["join", "inner", "left", "null", "combine", "tables"],
    "Subqueries": ["subquery", "subqueries", "nested", "inside", "exists"],
}


def _setting(name):
    """Read a setting from an environment variable, then from Streamlit secrets."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def ai_provider():
    """Return (provider name, key) if a key is set, otherwise None."""
    key = _setting("GEMINI_API_KEY")
    if key:
        return "gemini", key
    key = _setting("ANTHROPIC_API_KEY")
    if key:
        return "claude", key
    return None


def ai_available():
    return ai_provider() is not None


def _log_error(where, error):
    """Print a short, safe error line in the server log (Render Logs). Never prints the key."""
    if isinstance(error, ValueError):
        message = "(hidden for safety, may contain a header value)"
    else:
        message = str(error)
        for name in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
            secret = _setting(name)
            if secret:
                message = message.replace(secret, "[hidden]")
    print(f"[SQLMentor AI] {where} failed: {type(error).__name__}: {message[:300]}",
          file=sys.stderr, flush=True)


def _post(url, body, headers):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # Keep only the HTTP status and a short message from the API
        detail = error.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"HTTP {error.code}: {detail}") from None

def ask_llm(system, messages, max_tokens=300):
    """Send a chat to the AI and return its text.

    messages looks like [{"role": "user", "content": "..."}, ...]
    It raises an error if something goes wrong. The callers below catch it.
    """
    provider = ai_provider()
    if provider is None:
        raise RuntimeError("No API key is set.")
    name, key = provider

    # The first message must be from the user, for both providers
    messages = list(messages)
    while messages and messages[0]["role"] != "user":
        messages.pop(0)

    if name == "gemini":
        model = _setting("GEMINI_MODEL") or GEMINI_MODEL
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]}
                for m in messages
            ],
            # Gemini may use some tokens for thinking, so we allow more room
            "generationConfig": {"maxOutputTokens": max(max_tokens, 800), "temperature": 0.3},
        }
        data = _post(GEMINI_URL.format(model=model), body,
                     {"content-type": "application/json", "x-goog-api-key": key})
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts).strip()

    model = _setting("CLAUDE_MODEL") or CLAUDE_MODEL
    body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
    data = _post(CLAUDE_URL, body, {
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    return data["content"][0]["text"].strip()


# ---------- Hints (Practice mode) ----------

def fallback_hint(question: dict, reason: str, level: int = 0) -> str:
    """Hint without AI. 'level' 0, 1, 2 gives a stronger hint each time."""
    general = REASON_HINTS.get(reason, "")
    hints = question.get("hints", [])
    step = hints[min(level, len(hints) - 1)] if hints else ""
    return (general + " " + step).strip()


def get_hint(question, user_sql, status, reason, error=None, level=0) -> dict:
    """Return {"text": ..., "source": "ai" or "fallback"}."""
    if ai_available():
        try:
            prompt = HINT_TEMPLATE.format(
                scenario=question["scenario"], task=question["task"],
                status=status, reason=reason, error=error or "none",
                sql=(user_sql or "")[:1000])
            text = ask_llm(TUTOR_SYSTEM, [{"role": "user", "content": prompt}], 200)
            if text:
                return {"text": text, "source": "ai"}
        except Exception as error:
            _log_error("get_hint", error) # any problem: use the simple hint below
    return {"text": fallback_hint(question, reason, level), "source": "fallback"}


# ---------- Ask a Doubt (chat) ----------

def fallback_doubt(text, lessons) -> str:
    """Answer a doubt from the lessons when the AI is not available."""
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    best, best_score = None, 0
    for lesson in lessons:
        score = len(words & set(LESSON_WORDS.get(lesson["module"], [])))
        if score > best_score:
            best, best_score = lesson, score
    if best is None:
        names = ", ".join(lesson["module"] for lesson in lessons)
        return "AI help is not connected right now. You can ask about: " + names + "."
    return (f"AI help is not connected right now, but this lesson may help.\n\n"
            f"**{best['module']}:** {best['explanation']}")


def get_doubt_answer(history, lessons) -> dict:
    """Answer the last question in the chat. history = list of {"role", "content"}."""
    if ai_available():
        try:
            text = ask_llm(TUTOR_SYSTEM, history[-8:], 350)
            if text:
                return {"text": text, "source": "ai"}
        except Exception as error:
            _log_error("get_hint", error)
    last = history[-1]["content"] if history else ""
    return {"text": fallback_doubt(last, lessons), "source": "fallback"}


# ---------- Explain differently (Learn mode) ----------

def explain_lesson(lesson) -> dict:
    """Explain a lesson again in a different way."""
    if ai_available():
        try:
            prompt = LESSON_TEMPLATE.format(
                module=lesson["module"], explanation=lesson["explanation"],
                example=lesson["example"])
            text = ask_llm(TUTOR_SYSTEM, [{"role": "user", "content": prompt}], 300)
            if text:
                return {"text": text, "source": "ai"}
        except Exception as error:
            _log_error("get_hint", error)
    return {"text": "AI help is not connected right now. Read the key points again, "
                    "then press Run example to see the result.", "source": "fallback"}


# ---------- Learning feedback (summary and PDF) ----------

def fallback_feedback(summary) -> str:
    """Feedback written from the numbers, when the AI is not available."""
    accuracy = summary["overall_accuracy"]
    if accuracy is None:
        return "You have not answered any question yet. Start with Practice mode to get your feedback."
    parts = [f"Your level is {summary['level']} and your overall accuracy is {accuracy}%."]
    if summary["strengths"]:
        parts.append("You are strong in " + ", ".join(summary["strengths"]) + ".")
    if summary["weak_areas"]:
        parts.append("You need more practice in " + ", ".join(summary["weak_areas"]) + ".")
    parts.append(summary["recommendation"])
    return " ".join(parts)


def get_feedback(summary) -> dict:
    """Return {"text": ..., "source": "ai" or "fallback"}. Only numbers go to the AI."""
    if ai_available() and summary["overall_accuracy"] is not None:
        try:
            lines = []
            for module, s in summary["topic_progress"].items():
                if s["attempted"] == 0:
                    lines.append(f"- {module}: not tried yet")
                else:
                    lines.append(f"- {module}: solved {s['correct']} of {s['attempted']} "
                                 f"tried, {s['accuracy']}%")
            prompt = FEEDBACK_TEMPLATE.format(
                level=summary["level"], accuracy=f"{summary['overall_accuracy']}%",
                modules="\n".join(lines))
            text = ask_llm(TUTOR_SYSTEM, [{"role": "user", "content": prompt}], 250)
            if text:
                return {"text": text, "source": "ai"}
        except Exception as error:
            _log_error("get_hint", error) # any problem: use the simple feedback below
    return {"text": fallback_feedback(summary), "source": "fallback"}


if __name__ == "__main__":
    # Quick test without internet. Run from the project folder: python -m src.llm_coach
    from src.evaluator import load_questions

    q1 = load_questions()[0]
    for level in range(3):
        print(level, "->", fallback_hint(q1, "extra_rows", level))
    lessons = [{"module": m, "explanation": "Example text for " + m, "example": "SELECT 1"}
               for m in LESSON_WORDS]
    print(fallback_doubt("How does a left join work?", lessons))
    print(fallback_doubt("What is the weather today?", lessons))
    print("AI key found:", ai_available())