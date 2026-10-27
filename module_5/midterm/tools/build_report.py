"""Build the SG5 evidence report from the committed machine-readable results.

Run with the documented PDF-authoring environment, not the vision environment:
    python module_5/midterm/tools/build_report.py --render-dir tmp/report_review
Requires reportlab; optional page rendering requires pypdfium2 and Pillow.
No inference, evaluation, network access or Git operation occurs in this builder.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab import rl_config
from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (Image, PageBreak, Paragraph,
                               SimpleDocTemplate, Spacer, Table, TableStyle)


rl_config.warnOnMissingFontGlyphs = 1
PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = PACKAGE.parents[1]
RESULTS = PACKAGE / "results"
REPORT = PACKAGE / "report"
BRANCH = "sg5-midterm-integration"
GITHUB = "https://github.com/Sananismm/CV_Drowsinees_Detection"
BOARD = "https://github.com/users/Sananismm/projects/2"
INK = colors.HexColor("#182B45")
BLUE = colors.HexColor("#245D83")
TEAL = colors.HexColor("#237479")
MUTED = colors.HexColor("#536274")
LINE = colors.HexColor("#CBD5E0")
PALE = colors.HexColor("#F2F5F8")
AMBER = colors.HexColor("#875D21")
PAGE_W, PAGE_H = A4
WIDTH = PAGE_W - 92


STYLES = {
    "title": ParagraphStyle("ReportTitle", fontName="Helvetica-Bold", fontSize=25,
                            leading=30, textColor=INK, spaceAfter=13),
    "subtitle": ParagraphStyle("ReportSubtitle", fontName="Helvetica", fontSize=12,
                               leading=17, textColor=MUTED, spaceAfter=13),
    "eyebrow": ParagraphStyle("ReportEyebrow", fontName="Helvetica-Bold", fontSize=8.4,
                              leading=12, textColor=BLUE, spaceAfter=9),
    "h1": ParagraphStyle("ReportH1", fontName="Helvetica-Bold", fontSize=18,
                         leading=23, textColor=INK, spaceAfter=12),
    "h2": ParagraphStyle("ReportH2", fontName="Helvetica-Bold", fontSize=11,
                         leading=15, textColor=INK, spaceBefore=8, spaceAfter=6),
    "body": ParagraphStyle("ReportBody", fontName="Helvetica", fontSize=9.6,
                           leading=13.8, textColor=INK, spaceAfter=8),
    "small": ParagraphStyle("ReportSmall", fontName="Helvetica", fontSize=8.3,
                            leading=11.7, textColor=MUTED, spaceAfter=6),
    "cell": ParagraphStyle("ReportCell", fontName="Helvetica", fontSize=8.3,
                           leading=11.3, textColor=INK),
    "cellsmall": ParagraphStyle("ReportCellSmall", fontName="Helvetica", fontSize=7.7,
                                leading=10.3, textColor=INK),
    "header": ParagraphStyle("ReportTableHeader", fontName="Helvetica-Bold", fontSize=8.1,
                             leading=10.6, textColor=colors.white),
    "code": ParagraphStyle("ReportCode", fontName="Courier", fontSize=7.9,
                           leading=10.7, textColor=INK, backColor=PALE,
                           borderPadding=9, spaceAfter=10),
    "caption": ParagraphStyle("ReportCaption", fontName="Helvetica", fontSize=8.1,
                              leading=11.3, textColor=MUTED, spaceBefore=5, spaceAfter=9),
}


def p(text, style="body"):
    return Paragraph(text, STYLES[style])


def text(value):
    return escape(str(value))


def table(headers, rows, widths, small=False):
    cellstyle = "cellsmall" if small else "cell"
    data = [[p(text(h), "header") for h in headers]]
    for row in rows:
        data.append([p(str(value), cellstyle) for value in row])
    item = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), .5, BLUE),
        ("LINEBELOW", (0, 1), (-1, -1), .35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
    ]))
    return item


def code(lines):
    return p("<br/>".join(text(line).replace(" ", "&#160;") for line in lines.splitlines()), "code")


def heading(story, number, title):
    if story:
        story.append(PageBreak())
    story.append(p("SG5 MIDTERM EVIDENCE REPORT", "eyebrow"))
    story.append(p(f"{number}  {title}", "h1"))


def caption(story, number, description):
    story.append(p(f"Figure {number}. {description}", "caption"))


def box(drawing, x, y, width, height, title, lines=(), fill=PALE, accent=BLUE):
    drawing.add(Rect(x, y, width, height, rx=5, ry=5, fillColor=fill,
                     strokeColor=LINE, strokeWidth=.8))
    drawing.add(String(x + width / 2, y + height - 17, title,
                       fontName="Helvetica-Bold", fontSize=9.1,
                       fillColor=accent, textAnchor="middle"))
    for i, line in enumerate(lines):
        drawing.add(String(x + width / 2, y + height - 31 - i * 11, line,
                           fontName="Helvetica", fontSize=7.8,
                           fillColor=INK, textAnchor="middle"))


def arrow(drawing, points, label=None, label_xy=None, stroke=BLUE):
    for a, b in zip(points, points[1:]):
        drawing.add(Line(a[0], a[1], b[0], b[1], strokeColor=stroke, strokeWidth=1.2))
    a, b = points[-2:]
    if abs(b[0] - a[0]) > abs(b[1] - a[1]):
        direction = 1 if b[0] > a[0] else -1
        tip = [b[0], b[1], b[0] - 5 * direction, b[1] + 3,
               b[0] - 5 * direction, b[1] - 3]
    else:
        direction = 1 if b[1] > a[1] else -1
        tip = [b[0], b[1], b[0] - 3, b[1] - 5 * direction,
               b[0] + 3, b[1] - 5 * direction]
    drawing.add(Polygon(tip, fillColor=stroke, strokeColor=stroke))
    if label and label_xy:
        drawing.add(String(*label_xy, label, fontName="Helvetica", fontSize=7.5,
                           fillColor=MUTED, textAnchor="middle"))


def pipeline_diagram():
    drawing = Drawing(WIDTH, 295)
    box(drawing, 4, 205, 95, 53, "Source frames", ["Saved SG1 clips", "25 fps capture clock"])
    box(drawing, 127, 205, 110, 53, "SG1 landmarks", ["One detector", "Shared 478-point record"])
    box(drawing, 275, 242, 143, 51, "SG2 eye state", ["Selected EAR 0.15", "OPEN / CLOSED / UNKNOWN"])
    box(drawing, 275, 164, 143, 51, "SG3 adapter", ["Pixel MAR and hysteresis", "Causal mouth-open flag"])
    box(drawing, 4, 49, 143, 67, "SG4 TemporalEngine", ["Actual timestamp windows", "Closures and debounced events", "60 s PERCLOS / 10 Hz vectors"])
    box(drawing, 185, 49, 136, 67, "SG5 decision", ["Quality and timing checks", "Weighted state machine", "State plus observation status"], accent=TEAL)
    box(drawing, 359, 49, 140, 67, "SG6 consumer", ["Strict status-aware validation", "Visual / buzzer / fault requests", "No hardware side effects"])
    arrow(drawing, [(99, 231), (127, 231)])
    arrow(drawing, [(237, 231), (255, 231), (255, 267), (275, 267)])
    arrow(drawing, [(255, 231), (255, 189), (275, 189)])
    arrow(drawing, [(418, 267), (455, 267), (455, 140)])
    arrow(drawing, [(418, 189), (455, 189), (455, 140), (75, 140), (75, 116)])
    drawing.add(String(265, 145, "Synchronized identity, capture time and availability", fontSize=8,
                       fontName="Helvetica", fillColor=MUTED, textAnchor="middle"))
    arrow(drawing, [(147, 82), (185, 82)], "v1.1", (166, 91))
    arrow(drawing, [(321, 82), (359, 82)], "v2", (340, 91))
    drawing.add(String(251, 18, "PC integration verified; physical Jetson, camera and GPIO acceptance remain open",
                       fontName="Helvetica", fontSize=8.3, fillColor=AMBER, textAnchor="middle"))
    return drawing


def decision_diagram():
    drawing = Drawing(WIDTH, 265)
    box(drawing, 162, 225, 178, 35, "SG4 vector and source clock", [])
    drawing.add(Polygon([251, 215, 332, 178, 251, 141, 170, 178],
                        strokeColor=LINE, fillColor=PALE, strokeWidth=.8))
    drawing.add(String(251, 181, "Current evidence usable?", fontName="Helvetica-Bold",
                       fontSize=8.5, textAnchor="middle", fillColor=BLUE))
    drawing.add(String(251, 168, "Face, eyes, quality, time", fontName="Helvetica",
                       fontSize=7.6, textAnchor="middle", fillColor=INK))
    arrow(drawing, [(251, 225), (251, 215)])
    box(drawing, 164, 91, 174, 37, "Normalize, weight and smooth", [])
    arrow(drawing, [(251, 141), (251, 128)], "Yes", (263, 134))
    box(drawing, 378, 106, 122, 49, "Untrusted observation", ["Insufficient or stale", "Fault request; no trusted alert"],
        fill=colors.HexColor("#FCF6E9"), accent=AMBER)
    arrow(drawing, [(332, 178), (439, 178), (439, 155)], "No", (386, 184), stroke=AMBER)
    arrow(drawing, [(340, 243), (480, 243), (480, 155)], "Capture silence > 0.5 s", (421, 249), stroke=AMBER)
    box(drawing, 3, 11, 139, 48, "NORMAL", ["No drowsiness request"])
    box(drawing, 182, 11, 139, 48, "WARNING", ["Visual warning request"])
    box(drawing, 361, 11, 139, 48, "DROWSY", ["Visual + buzzer request"], accent=TEAL)
    arrow(drawing, [(251, 91), (251, 74), (72, 74), (72, 59)])
    arrow(drawing, [(251, 74), (251, 59)])
    arrow(drawing, [(251, 74), (430, 74), (430, 59)])
    drawing.add(String(251, 78, "Hysteresis plus entry and release confirmation", fontName="Helvetica",
                       fontSize=7.7, textAnchor="middle", fillColor=MUTED))
    drawing.add(String(251, -3, "Valid prolonged closure >= 1.5 s bypasses score confirmation and selects DROWSY",
                       fontName="Helvetica", fontSize=8, textAnchor="middle", fillColor=TEAL))
    return drawing


def results_diagram(overall):
    drawing = Drawing(WIDTH, 182)
    labels = ["A", "B", "C old", "C robust", "C fast"]
    palette = [colors.HexColor(value) for value in ("#C7762C", "#7D72A9", "#3A8979", "#326E9B", "#A26590")]
    for offset, key, title, maximum in ((8, "macro_f1", "Sample macro F1", 1.0),
                                        (268, "false_drowsy_duration_s", "False DROWSY duration in seconds", 10.0)):
        drawing.add(String(offset + 105, 169, title, fontName="Helvetica-Bold", fontSize=9.1,
                           fillColor=INK, textAnchor="middle"))
        base, top = 30, 140
        drawing.add(Line(offset, base, offset + 220, base, strokeColor=LINE))
        for fraction in (0, .5, 1):
            y = base + (top - base) * fraction
            drawing.add(Line(offset, y, offset + 220, y, strokeColor=LINE, strokeWidth=.4))
        for i, row in enumerate(overall):
            value = row[key]
            height = value / maximum * (top - base)
            x = offset + 8 + i * 43
            drawing.add(Rect(x, base, 27, max(height, .4), fillColor=palette[i], strokeColor=None))
            drawing.add(String(x + 13.5, base + height + 6, f"{value:.2f}", textAnchor="middle",
                               fontName="Helvetica", fontSize=8, fillColor=INK))
            drawing.add(String(x + 13.5, 15, labels[i], textAnchor="middle", fontName="Helvetica",
                               fontSize=7.6, fillColor=MUTED))
    return drawing


def footer(canvas, document):
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.7)
    canvas.drawString(46, 24, "CS477  |  G1-D2 SG5  |  Rafed Aftab and Filza Umar")
    canvas.drawRightString(PAGE_W - 46, 24, f"28 October 2026  |  {document.page}")
    canvas.restoreState()


def pct(value):
    return f"{100 * value:.1f}%"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_story(evidence, videos, sources, verification=None, pr_url=None):
    try:
        from .visual_report import build_story
    except ImportError:
        from visual_report import build_story
    return build_story(evidence, videos, sources, verification, pr_url, layout=globals())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT / "SG5_Midterm_Report.pdf")
    parser.add_argument("--render-dir", type=Path, help="Optional QA PNG directory; not a submission artifact")
    parser.add_argument("--pr-url", help="Published team review request URL, when available")
    args = parser.parse_args(argv)
    bundle_path = REPORT / "assets" / "evidence_bundle.json"
    if not bundle_path.exists():
        parser.error("Pinned visual evidence missing; run prepare_report_assets.py in the vision environment first.")
    bundle = load_json(bundle_path)
    evidence, videos, sources, verification = (bundle[key] for key in ("evaluation", "videos", "sources", "verification"))
    if args.pr_url is None and verification:
        args.pr_url = verification.get("pull_request")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(args.output), pagesize=A4, leftMargin=46, rightMargin=46,
                                topMargin=40, bottomMargin=43, title="SG5 Midterm Results and Integration Evidence",
                                author="Rafed Aftab 457967 and Filza Umar 464340", subject="CS477 G1-D2 midterm integration evidence")
    story = make_story(evidence, videos, sources, verification, args.pr_url)
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print("Report:", args.output.resolve())
    if args.render_dir:
        import pypdfium2 as pdfium
        args.render_dir.mkdir(parents=True, exist_ok=True)
        pdf = pdfium.PdfDocument(str(args.output))
        print("Pages:", len(pdf))
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=1.5)
            bitmap.to_pil().save(args.render_dir / f"page-{index + 1:02d}.png")
            bitmap.close()
            page.close()
        pdf.close()
        print("QA renders:", args.render_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
