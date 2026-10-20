"""PDF progress report for SQLMentor AI (optional extra).

It only prints numbers that progress.py already calculated.
It does not run SQL and it does not check answers.
"""
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"

INDIGO = (75, 63, 245)
DEEP_BLUE = (24, 42, 150)
LIGHT = (238, 240, 255)
LINE = (217, 220, 240)
GREY = (100, 100, 100)
DARK = (30, 30, 40)
GREEN = (22, 163, 74)
AMBER = (217, 119, 6)
RED = (220, 38, 38)
PURPLE = (124, 58, 237)
GOLD = (255, 200, 60)
SOFT_LINE = (175, 170, 250)  # light line on the indigo banner
PANEL_BORDER = INDIGO  # colour of the panel borders; change it to any (r, g, b)

# Colour and name for each result the evaluator can give
STATUS_COLOURS = [
    ("correct", "Correct", GREEN),
    ("partial", "Partly right", AMBER),
    ("incorrect", "Incorrect", RED),
    ("error", "SQL error", PURPLE),
]


def _safe(text):
    """The built-in PDF font only knows basic Latin letters, so other letters become '?'."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _card(pdf, x, y, w, h, accent):
    """A white rounded card with a thin border and a coloured bar on the left."""
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.3)
    pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=3)
    pdf.set_fill_color(*accent)
    pdf.rect(x, y + 3, 1.6, h - 6, style="F")


def _title(pdf, text, x, y, w):
    """Centered section heading inside a rounded box with a border."""
    pdf.set_font("Helvetica", "B", 13)
    box_w = pdf.get_string_width(text) + 14
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*INDIGO)
    pdf.set_line_width(0.6)
    pdf.rect(x + (w - box_w) / 2, y, box_w, 9, style="DF", round_corners=True, corner_radius=3)
    pdf.set_xy(x, y)
    pdf.set_text_color(*DEEP_BLUE)
    pdf.cell(w, 9, text, align="C")

def _panel(pdf, x, y, w, h, title):
    """A rounded panel with a light shadow, a coloured border and a heading on its top edge."""
    pdf.set_fill_color(226, 229, 243)
    pdf.rect(x + 0.9, y + 0.9, w, h, style="F", round_corners=True, corner_radius=4)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*PANEL_BORDER)
    pdf.set_line_width(0.5)
    pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=4)
    _title(pdf, title, x, y - 4.5, w)


def _pie(pdf, cx, cy, radius, counts):
    """Draw a pie chart of the answer results. Returns nothing."""
    total = sum(counts.values())
    if total == 0:
        pdf.set_fill_color(*LIGHT)
        pdf.ellipse(cx - radius, cy - radius, radius * 2, radius * 2, style="F")
        pdf.set_xy(cx - radius, cy - 3)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GREY)
        pdf.cell(radius * 2, 6, "No answers yet", align="C")
        return

    start = 90.0  # the first slice starts at the top and goes clockwise
    for key, _name, colour in STATUS_COLOURS:
        count = counts.get(key, 0)
        if count == 0:
            continue
        pdf.set_fill_color(*colour)
        if count == total:
            pdf.ellipse(cx - radius, cy - radius, radius * 2, radius * 2, style="F")
            continue
        end = start - 360.0 * count / total
        # A slice is a polygon: the centre point, then points along the edge
        points = [(cx, cy)]
        steps = max(2, int((start - end) / 3))
        for i in range(steps + 1):
            angle = math.radians(start - (start - end) * i / steps)
            points.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
        pdf.polygon(points, style="F")
        start = end
    # White circle in the middle makes it a donut
    pdf.set_fill_color(255, 255, 255)
    inner = radius * 0.55
    pdf.ellipse(cx - inner, cy - inner, inner * 2, inner * 2, style="F")
    pdf.set_xy(cx - inner, cy - 5)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*DEEP_BLUE)
    pdf.cell(inner * 2, 6, str(total), align="C")
    pdf.set_xy(cx - inner, cy + 1)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*GREY)
    pdf.cell(inner * 2, 4, "answers", align="C")


def build_report(learner, summary, attempts, feedback=None):
    """Make a one-page PDF report and return it as bytes.

    If the learner asked for learning feedback, it is printed at the bottom of the same page.
    """
    # Imported here, so the app still runs if fpdf2 is not installed
    from fpdf import FPDF

    counts = Counter(a["status"] for a in attempts)
    accuracy = summary["overall_accuracy"]
    progress = summary["topic_progress"]
    solved = sum(s["correct"] for s in progress.values())
    tried = sum(s["attempted"] for s in progress.values())
    hints = sum(int(a.get("hints_used", 0)) for a in attempts)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # ---------- Top band: logo, centered title ----------
    pdf.set_fill_color(*INDIGO)
    pdf.rect(0, 0, 210, 34, "F")
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(15, 4, 26, 26, style="F", round_corners=True, corner_radius=5)
    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=19, y=7, h=20)
    # Two-colour title: a small white line with rules on both sides, then a big gold title
    subtitle = "Learner Progress Report"
    pdf.set_font("Helvetica", "", 12)
    sub_w = pdf.get_string_width(subtitle)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 6)
    pdf.cell(180, 7, subtitle, align="C")
    pdf.set_draw_color(*SOFT_LINE)
    pdf.set_line_width(0.5)
    pdf.line(58, 9.5, 105 - sub_w / 2 - 4, 9.5)
    pdf.line(105 + sub_w / 2 + 4, 9.5, 152, 9.5)
    pdf.line(58, 28.5, 152, 28.5)  # light line under the title
    pdf.set_text_color(*GOLD)
    pdf.set_xy(15, 14)
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(180, 12, "SQLMentor AI", align="C")

    # ---------- Learner line ----------
    pdf.set_fill_color(*LIGHT)
    pdf.rect(15, 36, 180, 9, style="F", round_corners=True, corner_radius=3)
    pdf.set_xy(20, 36)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*GREY)
    pdf.cell(17, 9, "LEARNER")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*DEEP_BLUE)
    pdf.cell(75, 9, _safe(learner)[:30])
    pdf.set_xy(122, 36)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*GREY)
    pdf.cell(11, 9, "DATE")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*DEEP_BLUE)
    pdf.cell(60, 9, datetime.now().strftime("%d %B %Y"))

    # ---------- Panel 1: overview (four stat cards) ----------
    top = 52
    _panel(pdf, 15, top, 180, 26, "Overview")
    stats = [
        ("LEVEL", summary["level"], INDIGO),
        ("OVERALL ACCURACY", "-" if accuracy is None else f"{accuracy}%", GREEN),
        ("QUESTIONS SOLVED", f"{solved} / {tried}", AMBER),
        ("HINTS USED", str(hints), PURPLE),
    ]
    card_w, gap = 39.5, 4
    for number, (label, value, colour) in enumerate(stats):
        x = 20 + number * (card_w + gap)
        _card(pdf, x, top + 6, card_w, 17, colour)
        pdf.set_xy(x + 5, top + 8)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*GREY)
        pdf.cell(card_w - 7, 4, label)
        pdf.set_xy(x + 5, top + 13.5)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*DEEP_BLUE)
        pdf.cell(card_w - 7, 7, _safe(value))

    # ---------- Panels 2 and 3: pie chart (left) and key points (right) ----------
    row_y = top + 26 + 8
    points = [
        ("Strong modules", ", ".join(summary["strengths"]) or "None yet", GREEN),
        ("Weak modules", ", ".join(summary["weak_areas"]) or "None yet", AMBER),
        ("Next step", summary["recommendation"], INDIGO),
    ]
    # Measure the text first, so the panel and every card are always tall enough
    pdf.set_font("Helvetica", "B", 9)
    measured = []
    for label, text, colour in points:
        lines = pdf.multi_cell(84, 4.2, _safe(text), align="L", dry_run=True, output="LINES")
        measured.append((label, text, colour, 8 + 4.2 * len(lines)))
    row_h = max(58, 7 + sum(m[3] for m in measured) + 2.5 * (len(measured) - 1) + 4)

    _panel(pdf, 15, row_y, 72, row_h, "Answer results")
    _pie(pdf, 34, row_y + row_h / 2 + 2, 15, counts)
    legend_y = row_y + row_h / 2 - 12
    for key, name, colour in STATUS_COLOURS:
        pdf.set_fill_color(*colour)
        pdf.rect(53, legend_y + 1.2, 3.5, 3.5, style="F")
        pdf.set_xy(58, legend_y)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DARK)
        pdf.cell(28, 6, f"{name}: {counts.get(key, 0)}")
        legend_y += 7

    _panel(pdf, 92, row_y, 103, row_h, "Key points")
    point_y = row_y + 7
    for label, text, colour, height in measured:
        _card(pdf, 97, point_y, 93, height, colour)
        pdf.set_xy(102, point_y + 1.5)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(84, 4, label.upper())
        pdf.set_xy(102, point_y + 5.5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*DEEP_BLUE)
        pdf.multi_cell(84, 4.2, _safe(text), align="L", max_line_height=4.2)
        point_y += height + 2.5

    # ---------- Panel 4: module table with small bars ----------
    table_y = row_y + row_h + 8
    line_h = 7.2
    table_h = 5 + 9 + line_h * len(progress) + 4
    _panel(pdf, 15, table_y, 180, table_h, "Module summary")
    widths = (64, 24, 30, 52)
    head_y = table_y + 5
    pdf.set_xy(20, head_y)
    pdf.set_fill_color(*INDIGO)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    for width, title in zip(widths, ("Module", "Solved", "Submissions", "Accuracy")):
        pdf.cell(width, 9, ("  " + title) if title == "Module" else title,
                 fill=True, align="L" if title == "Module" else "C",
                 new_x="RIGHT", new_y="TOP")
    row_y2 = head_y + 9
    for number, (module, s) in enumerate(progress.items()):
        pdf.set_fill_color(*(LIGHT if number % 2 == 0 else (255, 255, 255)))
        pdf.rect(20, row_y2, 170, line_h, "F")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(20, row_y2)
        pdf.cell(widths[0], line_h, _safe("  " + module))
        pdf.cell(widths[1], line_h, f"{s['correct']}/{s['attempted']}", align="C")
        pdf.cell(widths[2], line_h, str(s["submissions"]), align="C")
        # small bar and the percent
        bar_x = 20 + sum(widths[:3]) + 3
        pdf.set_fill_color(225, 228, 245)
        pdf.rect(bar_x, row_y2 + 1.9, 32, 3.4, "F")
        if s["accuracy"] > 0:
            pdf.set_fill_color(*INDIGO)
            pdf.rect(bar_x, row_y2 + 1.9, 32 * s["accuracy"] / 100, 3.4, "F")
        pdf.set_xy(bar_x + 34, row_y2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*DEEP_BLUE)
        pdf.cell(14, line_h, f"{s['accuracy']}%")
        row_y2 += line_h

    # ---------- Panel 5: level guide ----------
    guide_y = table_y + table_h + 8
    _panel(pdf, 15, guide_y, 180, 22, "Level guide")
    pdf.set_xy(15, guide_y + 4.5)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*GREY)
    pdf.cell(180, 4, "Your level changes with your overall accuracy.", align="C")
    levels = [("Beginner", "Below 50%"), ("Intermediate", "50% to 80%"), ("Advanced", "Above 80%")]
    box_w = 53
    for number, (name, rule) in enumerate(levels):
        x = 20 + number * (box_w + 5.5)
        y = guide_y + 9.5
        active = name == summary["level"]
        pdf.set_fill_color(*(INDIGO if active else LIGHT))
        pdf.rect(x, y, box_w, 10, style="F", round_corners=True, corner_radius=3)
        pdf.set_xy(x, y + 1)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*((255, 255, 255) if active else DEEP_BLUE))
        pdf.cell(box_w, 4, name, align="C")
        pdf.set_xy(x, y + 5)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(box_w, 4, rule, align="C")
    end_y = guide_y + 22

    # ---------- Panel 6: learning feedback (only if the learner asked for it) ----------
    if feedback:
        text = _safe(feedback["text"].replace("*", "").strip())
        fb_y = end_y + 8
        max_lines = max(2, int((286 - fb_y - 13) / 4.6))  # lines that fit above the footer
        pdf.set_font("Helvetica", "", 9.5)
        lines = pdf.multi_cell(170, 4.6, text, dry_run=True, output="LINES")
        while len(lines) > max_lines and len(text) > 10:  # too long: cut the text so the report stays on one page
            text = text[: int(len(text) * 0.9)].rstrip() + "..."
            lines = pdf.multi_cell(170, 4.6, text, dry_run=True, output="LINES")
        fb_h = 6 + 4.6 * len(lines) + 7
        _panel(pdf, 15, fb_y, 180, fb_h, "Learning feedback")
        pdf.set_xy(20, fb_y + 6)
        pdf.set_font("Helvetica", "", 9.5)  # the panel heading changed the font, so set it again
        pdf.set_text_color(*DARK)
        pdf.multi_cell(170, 4.6, text)
        source = ("Written by an AI tutor from your results."
                  if feedback["source"] == "ai"
                  else "Written from your results.")
        pdf.set_xy(20, fb_y + fb_h - 6)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(170, 4, source)
        end_y = fb_y + fb_h

    # ---------- Footer note ----------
    pdf.set_xy(15, min(end_y + 5, 290))
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(180, 4, "Generated by SQLMentor AI. SQLite checks every answer, so these "
             "results come from the database, not from an AI model.", align="C")

    return bytes(pdf.output())