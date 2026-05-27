"""One-shot helper: produce a multi-page text PDF from a wiki .txt so we can test
the pypdf extraction path. Output: app/sample_data/test_lecture.pdf

Run from repo root:  python scripts/gen_test_pdf.py
Prereq:              pip install reportlab"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

repo_root = Path(__file__).parent.parent
sample_dir = repo_root / "app" / "sample_data"
src = (sample_dir / "wiki_04_photosynthesis.txt").read_text(encoding="utf-8")

styles = getSampleStyleSheet()
title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=18, spaceAfter=12)
slide_style = ParagraphStyle("slide", parent=styles["Heading2"], fontSize=14, spaceAfter=8)
body = styles["BodyText"]

# Split source text into "slides" — chunks of ~600 chars to simulate slide deck
paragraphs = [p.strip() for p in src.split("\n\n") if p.strip()]
slides = []
current, current_len = [], 0
for p in paragraphs:
    if current_len + len(p) > 600 and current:
        slides.append("\n".join(current))
        current, current_len = [], 0
    current.append(p)
    current_len += len(p)
if current:
    slides.append("\n".join(current))

out = sample_dir / "test_lecture.pdf"
doc = SimpleDocTemplate(str(out), pagesize=letter,
                        leftMargin=0.7*inch, rightMargin=0.7*inch,
                        topMargin=0.7*inch, bottomMargin=0.7*inch)
story = [Paragraph("Photosynthesis — Lecture Notes", title_style)]
for i, slide in enumerate(slides, 1):
    story.append(Paragraph(f"Slide {i}", slide_style))
    story.append(Paragraph(slide.replace("\n", "<br/>"), body))
    story.append(Spacer(1, 0.2*inch))
    if i < len(slides):
        story.append(PageBreak())

doc.build(story)
print(f"Wrote {out} ({out.stat().st_size:,} bytes, {len(slides)} slides)")
