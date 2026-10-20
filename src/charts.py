"""Progress bars for SQLMentor AI (optional extra)."""
import html

import streamlit as st


def show_topic_chart(scores: dict):
    """Show one progress bar for each module.

    scores looks like {"SELECT + WHERE": 80, "Subqueries": 50} (percent).
    A module with 0 percent still shows an empty bar.
    """
    if not scores:
        st.info("No attempts yet. Solve some questions to see your progress.")
        return

    rows = ""
    for module, value in scores.items():
        percent = max(0, min(100, int(value)))
        rows += (
            '<div class="sm-bar-row">'
            f'<div class="sm-bar-name">{html.escape(module)}</div>'
            f'<div class="sm-bar-track"><div class="sm-bar-fill" style="width:{percent}%"></div></div>'
            f'<div class="sm-bar-pct">{percent}%</div>'
            "</div>"
        )
    st.markdown(f'<div class="sm-card sm-bars">{rows}</div>', unsafe_allow_html=True)