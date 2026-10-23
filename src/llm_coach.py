
"""AI helper for SQLMentor AI.

The AI provides hints, explanations, and coaching only.
SQLite decides whether a learner's SQL answer is correct.
The expected answer is never sent to the AI.

Provider order:
1. Gemini
2. Groq
3. Built-in fallback if both providers fail

API keys are read from environment variables or Streamlit secrets.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

from src.prompts import (
    FEEDBACK_TEMPLATE,
    HINT_TEMPLATE,
    LESSON_TEMPLATE,
    TUTOR_SYSTEM,
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/{model}:generateContent"
)
GEMINI_MODEL = "gemini-3.8-flash"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"

USER_AGENT = "SQLMentorAI/1.0"


REASON_HINTS = {
    "sql_error": "Your query has an error. Check spelling, commas and table names.",
    "wrong_columns": "The number of columns is not right. Read the task again.",
    "wrong_values": "The values are different. Check your WHERE or JOIN condition.",
    "extra_rows": "You have extra rows. Do you need a filter?",
    "missing_rows": "Some rows are missing. Is your filter too strict?",
    "wrong_order": "The rows are right, but the order is not. Think about ORDER BY.",
}

LESSON_WORDS = {
    "SELECT + WHERE": [
        "select", "where", "filter", "column", "condition", "rows"
    ],
    "Aggregate Functions": [
        "count", "sum", "avg", "average", "min", "max", "total", "aggregate"
    ],
    "GROUP BY + HAVING": ["group", "having", "each", "per"],
    "INNER JOIN + LEFT JOIN": [
        "join", "inner", "left", "null", "combine", "tables"
    ],
    "Subqueries": [
        "subquery", "subqueries", "nested", "inside", "exists"
    ],
}


def _setting(name):
    """Read a setting from environment variables, then Streamlit secrets."""
    value = os.environ.get(name)
    if value:
        return value

    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def ai_providers():
    """Return configured providers in priority order: Gemini, then Groq."""
    providers = []

    gemini_key = _setting("GEMINI_API_KEY")
    if gemini_key:
        providers.append(("gemini", gemini_key))

    groq_key = _setting("GROQ_API_KEY")
    if groq_key:
        providers.append(("groq", groq_key))

    return providers


def ai_provider():
    """Return the first configured provider, or None."""
    providers = ai_providers()
    return providers[0] if providers else None


def ai_available():
    """Return True if at least one AI provider is configured."""
    return bool(ai_providers())


class APIRequestError(RuntimeError):
    """HTTP error with a limited diagnostic message."""

    def __init__(self, status_code, detail=""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}")


def _log_error(where, error, provider=None):
    """Log limited diagnostics without intentionally logging API keys."""
    status = getattr(error, "status_code", None)
    detail = getattr(error, "detail", "")

    if status:
        details = f"HTTP {status}"
        if detail:
            details += f" | {detail}"
    else:
        details = type(error).__name__

    print(
        f"[SQLMentor AI] {where} | {provider or 'AI'} | {details}",
        file=sys.stderr,
        flush=True,
    )


def _post(url, body, headers):
    """Send a JSON POST request and capture limited HTTP diagnostics."""
    request_headers = dict(headers)
    request_headers.setdefault("User-Agent", USER_AGENT)

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        detail = ""

        try:
            payload = json.loads(
                error.read().decode("utf-8", errors="replace")
            )
            provider_error = payload.get("error", {})

            if isinstance(provider_error, dict):
                detail = str(provider_error.get("message", ""))

        except (ValueError, TypeError, AttributeError):
            pass

        # Redact common credential formats and limit log length.
        detail = re.sub(
            r"(?i)\bBearer\s+\S+",
            "Bearer [REDACTED]",
            detail,
        )
        detail = re.sub(
            r"(?i)\b(api[_ -]?key|token|authorization)\s*[:=]\s*\S+",
            r"\1=[REDACTED]",
            detail,
        )
        detail = detail[:240]

        raise APIRequestError(error.code, detail) from None


def _clean_chat_messages(messages):
    """Keep only supported chat fields and valid chat roles."""
    clean_messages = []

    for message in messages:
        role = message.get("role")
        content = message.get("content")

        if role not in ("user", "assistant"):
            continue

        if not isinstance(content, str) or not content.strip():
            continue

        clean_messages.append({
            "role": role,
            "content": content,
        })

    # Both providers expect the conversation to begin with a user message.
    while clean_messages and clean_messages[0]["role"] != "user":
        clean_messages.pop(0)

    return clean_messages


def ask_llm(system, messages, max_tokens=300):
    """Try Gemini, then Groq. Return answer text and actual provider."""
    providers = ai_providers()

    if not providers:
        raise RuntimeError("No AI provider is configured.")

    clean_messages = _clean_chat_messages(list(messages))

    if not clean_messages:
        raise RuntimeError("No valid user message was provided.")

    for name, key in providers:
        try:
            if name == "gemini":
                model = _setting("GEMINI_MODEL") or GEMINI_MODEL

                body = {
                    "system_instruction": {
                        "parts": [{"text": system}]
                    },
                    "contents": [
                        {
                            "role": (
                                "model"
                                if message["role"] == "assistant"
                                else "user"
                            ),
                            "parts": [{"text": message["content"]}],
                        }
                        for message in clean_messages
                    ],
                    "generationConfig": {
                        "maxOutputTokens": max(max_tokens, 800),
                        "temperature": 0.3,
                    },
                }

                data = _post(
                    GEMINI_URL.format(model=model),
                    body,
                    {
                        "content-type": "application/json",
                        "x-goog-api-key": key,
                    },
                )

                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError(
                        "Gemini returned no response candidates."
                    )

                parts = candidates[0].get("content", {}).get("parts", [])
                answer = "".join(
                    part.get("text", "") for part in parts
                ).strip()

            else:
                model = _setting("GROQ_MODEL") or GROQ_MODEL

                # Do not send Streamlit metadata such as "source" to Groq.
                groq_messages = [
                    {"role": "system", "content": system},
                    *[
                        {
                            "role": message["role"],
                            "content": message["content"],
                        }
                        for message in clean_messages
                    ],
                ]

                body = {
                    "model": model,
                    "messages": groq_messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                }

                data = _post(
                    GROQ_URL,
                    body,
                    {
                        "content-type": "application/json",
                        "Authorization": f"Bearer {key}",
                    },
                )

                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError(
                        "Groq returned no response choices."
                    )

                answer = choices[0].get("message", {}).get("content", "")
                answer = (answer or "").strip()

            if answer:
                return {
                    "text": answer,
                    "source": name,
                }

            raise RuntimeError("Provider returned empty text.")

        except Exception as error:
            _log_error("ask_llm", error, name)

    raise RuntimeError("All configured AI providers failed.")


# ---------- Hints (Practice mode) ----------

def fallback_hint(question: dict, reason: str, level: int = 0) -> str:
    """Return a built-in hint. Levels 0, 1, and 2 give stronger hints."""
    general = REASON_HINTS.get(reason, "")
    hints = question.get("hints", [])
    step = hints[min(max(level, 0), len(hints) - 1)] if hints else ""

    return (general + " " + step).strip()


def get_hint(
    question,
    user_sql,
    status,
    reason,
    error=None,
    level=0,
) -> dict:
    """Return a hint with its actual provider or fallback source."""
    if ai_available():
        try:
            prompt = HINT_TEMPLATE.format(
                scenario=question["scenario"],
                task=question["task"],
                status=status,
                reason=reason,
                error=error or "none",
                sql=(user_sql or "")[:1000],
            )

            answer = ask_llm(
                TUTOR_SYSTEM,
                [{"role": "user", "content": prompt}],
                200,
            )

            if answer["text"]:
                return answer

        except Exception as error:
            _log_error("get_hint", error)

    return {
        "text": fallback_hint(question, reason, level),
        "source": "fallback",
    }


# ---------- Ask a Doubt (chat) ----------

def fallback_doubt(text, lessons) -> str:
    """Suggest a relevant lesson when AI is unavailable."""
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    best, best_score = None, 0

    for lesson in lessons:
        score = len(
            words & set(LESSON_WORDS.get(lesson["module"], []))
        )
        if score > best_score:
            best, best_score = lesson, score

    if best is None:
        names = ", ".join(lesson["module"] for lesson in lessons)
        return (
            "AI help is not connected right now. "
            "You can ask about: " + names + "."
        )

    return (
        "AI help is not connected right now, but this lesson may help.\n\n"
        f"**{best['module']}:** {best['explanation']}"
    )


def get_doubt_answer(history, lessons) -> dict:
    """Answer the last question and identify the actual provider."""
    if ai_available():
        try:
            answer = ask_llm(TUTOR_SYSTEM, history[-8:], 350)
            if answer["text"]:
                return answer
        except Exception as error:
            _log_error("get_doubt_answer", error)

    last = history[-1].get("content", "") if history else ""

    return {
        "text": fallback_doubt(last, lessons),
        "source": "fallback",
    }


# ---------- Explain differently (Learn mode) ----------

def explain_lesson(lesson) -> dict:
    """Explain a lesson again and identify the actual provider."""
    if ai_available():
        try:
            prompt = LESSON_TEMPLATE.format(
                module=lesson["module"],
                explanation=lesson["explanation"],
                example=lesson["example"],
            )

            answer = ask_llm(
                TUTOR_SYSTEM,
                [{"role": "user", "content": prompt}],
                300,
            )

            if answer["text"]:
                return answer

        except Exception as error:
            _log_error("explain_lesson", error)

    return {
        "text": (
            "AI help is not connected right now. Read the key points again, "
            "then press Run example to see the result."
        ),
        "source": "fallback",
    }


# ---------- Learning feedback (summary and PDF) ----------

def fallback_feedback(summary) -> str:
    """Create feedback from learner progress without AI."""
    accuracy = summary["overall_accuracy"]

    if accuracy is None:
        return (
            "You have not answered any question yet. "
            "Start with Practice mode to get your feedback."
        )

    parts = [
        f"Your level is {summary['level']} and your overall accuracy is {accuracy}%."
    ]

    if summary["strengths"]:
        parts.append(
            "You are strong in " + ", ".join(summary["strengths"]) + "."
        )

    if summary["weak_areas"]:
        parts.append(
            "You need more practice in "
            + ", ".join(summary["weak_areas"]) + "."
        )

    parts.append(summary["recommendation"])
    return " ".join(parts)


def get_feedback(summary) -> dict:
    """Return feedback with its actual provider or fallback source."""
    if ai_available() and summary["overall_accuracy"] is not None:
        try:
            lines = []

            for module, progress in summary["topic_progress"].items():
                if progress["attempted"] == 0:
                    lines.append(f"- {module}: not tried yet")
                else:
                    lines.append(
                        f"- {module}: solved {progress['correct']} of "
                        f"{progress['attempted']} tried, "
                        f"{progress['accuracy']}%"
                    )

            prompt = FEEDBACK_TEMPLATE.format(
                level=summary["level"],
                accuracy=f"{summary['overall_accuracy']}%",
                modules="\n".join(lines),
            )

            answer = ask_llm(
                TUTOR_SYSTEM,
                [{"role": "user", "content": prompt}],
                250,
            )

            if answer["text"]:
                return answer

        except Exception as error:
            _log_error("get_feedback", error)

    return {
        "text": fallback_feedback(summary),
        "source": "fallback",
    }


if __name__ == "__main__":
    from src.evaluator import load_questions

    question = load_questions()[0]

    for level in range(3):
        print(
            level,
            "->",
            fallback_hint(question, "extra_rows", level),
        )

    lessons = [
        {
            "module": module,
            "explanation": "Example text for " + module,
            "example": "SELECT 1",
        }
        for module in LESSON_WORDS
    ]

    print(fallback_doubt("How does a left join work?", lessons))
    print(fallback_doubt("What is the weather today?", lessons))
    print("AI provider configured:", ai_available())
    print(
        "Configured providers:",
        ", ".join(name for name, _ in ai_providers()) or "none",
    )
