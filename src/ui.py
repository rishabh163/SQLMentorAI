"""Look and feel helpers for SQLMentor AI.

This file only draws things on the screen (CSS, images and small HTML cards).
It does not run SQL and it does not check answers.
"""
import base64
import html
import re
from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
CSS_PATH = ASSETS_DIR / "style.css"

# Small icons shown next to the mode names in the sidebar
MODE_ICONS = {"Learn": "📘 Learn", "Practice": "✍️ Practice", "Quiz": "🏆 Quiz", "Doubt": "💬 Ask a Doubt"}

# A clean font from Google Fonts. If there is no internet, the browser
# simply uses the next font in the list, so nothing breaks.
FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2"
    "?family=Inter:wght@400;500;600;700;800&display=swap');"
)


@st.cache_data
def _image_uri(name):
    """Read an image from the assets folder and turn it into text for HTML.

    A local file cannot be used directly inside HTML in Streamlit,
    so we convert it to base64. If the file is missing, we return "".
    """
    try:
        data = (ASSETS_DIR / name).read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _show(html_text, sidebar=False):
    """Show HTML on the page.

    Blank lines and spaces at the start of a line are removed,
    because Streamlit can break an HTML block that has them.
    """
    clean = "\n".join(line.strip() for line in html_text.splitlines() if line.strip())
    if sidebar:
        st.sidebar.markdown(clean, unsafe_allow_html=True)
    else:
        st.markdown(clean, unsafe_allow_html=True)


def load_css():
    """Read assets/style.css and apply it. If the file is missing, skip it."""
    try:
        css = CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return
    # The @import line must come first inside the style tag
    _show(f"<style>{FONT_IMPORT}\n{css}</style>")


def hero_banner():
    """Big banner at the top of the page: image on the left, text on the right."""
    uri = _image_uri("hero.png")
    image = f'<img class="sm-hero-img" src="{uri}" alt="">' if uri else ""
    _show(f"""
<div class="sm-hero">
<svg class="sm-hero-waves" viewBox="0 0 1000 300" preserveAspectRatio="none" aria-hidden="true">
<g fill="none" stroke="#ffffff" stroke-opacity="0.10" stroke-width="1.2">
<path d="M0 34 C250 -10 520 80 1000 14"/>
<path d="M0 52 C260 8 530 98 1000 32"/>
<path d="M0 270 C300 330 650 215 1000 285"/>
<path d="M0 288 C310 345 660 233 1000 303"/>
</g>
</svg>
{image}
<div class="sm-hero-text">
<div class="sm-hero-title">SQLMentor <span>AI</span></div>
<div class="sm-hero-code">SELECT skill FROM you WHERE practice &gt; 0;</div>
<div class="sm-hero-tags"><span>Learn</span><span>Practice</span><span>Quiz</span></div>
</div>
</div>
""")


def sidebar_brand():
    """Name box with the logo at the top of the sidebar."""
    uri = _image_uri("logo.png")
    image = f'<img class="sm-brand-img" src="{uri}" alt="">' if uri else ""
    _show(f"""
<div class="sm-brand">
{image}
<div>
<div class="sm-brand-title">SQL<span>Mentor</span></div>
<div class="sm-brand-sub">Learn. Practice. Improve.</div>
</div>
</div>
""", sidebar=True)


def sidebar_label(text):
    """Small grey heading in the sidebar, like PAGES in the dashboard."""
    _show(f'<div class="sm-label">{html.escape(text)}</div>', sidebar=True)


def sidebar_about():
    """Small About box at the bottom of the sidebar."""
    _show("""
<div class="sm-about">
<b>About</b><br>
Practice SQL with real scenarios. SQLite checks every answer, so the result is always fair.
</div>
""", sidebar=True)


def section_label(text):
    """Small coloured heading above a part of the page, like EXAMPLE QUERY."""
    _show(f'<div class="sm-section-label">{html.escape(text)}</div>')


def _keyword_chips(text):
    """Escape the text, then show ALL-CAPS words (SELECT, JOIN, NULL) as small code chips."""
    safe = html.escape(text)
    return re.sub(r"\b([A-Z][A-Z_]+)\b", r'<code class="sm-kw">\1</code>', safe)


def lesson_card(lesson):
    """Card for a lesson: big title, a coloured bar and key points.

    The explanation is split into sentences, and each sentence becomes one key point.
    """
    sentences = re.split(r"(?<=[.!?])\s+", lesson["explanation"].strip())
    points = "\n".join(f"<li>{_keyword_chips(s)}</li>" for s in sentences if s)
    _show(f"""
<div class="sm-card sm-lesson">
<div class="sm-lesson-title">{html.escape(lesson["module"])}</div>
<div class="sm-lesson-bar"></div>
<ul class="sm-points">
{points}
</ul>
</div>
""")


def question_card(question, title=None):
    """Card with the module, the level badge, the scenario and the task."""
    title = title or question["module"]
    level = question["difficulty"]
    _show(f"""
<div class="sm-card">
<div class="sm-card-head">
<span class="sm-card-title">{html.escape(title)}</span>
<span class="sm-badge sm-{html.escape(level.lower())}">{html.escape(level)}</span>
</div>
<div class="sm-scenario">{html.escape(question["scenario"])}</div>
<div class="sm-task"><b>Task:</b> {html.escape(question["task"])}</div>
</div>
""")


def score_card(score, total):
    """Big score box shown at the end of the quiz."""
    _show(f"""
<div class="sm-card sm-score">
<div class="sm-score-label">Your quiz score</div>
<div class="sm-score-number">{score} / {total}</div>
</div>
""")

    

def summary_cards(strengths, weak_areas, recommendation):
    """Three small cards: strong modules, weak modules and the next step."""
    strong = html.escape(", ".join(strengths) or "None yet")
    weak = html.escape(", ".join(weak_areas) or "None yet")
    step = html.escape(recommendation)
    _show(f"""
<div class="sm-mini-grid">
<div class="sm-mini sm-mini-good">
<div class="sm-mini-label">Strong modules</div>
<div class="sm-mini-value">{strong}</div>
</div>
<div class="sm-mini sm-mini-warn">
<div class="sm-mini-label">Weak modules</div>
<div class="sm-mini-value">{weak}</div>
</div>
<div class="sm-mini">
<div class="sm-mini-label">Next step</div>
<div class="sm-mini-value">{step}</div>
</div>
</div>
""")