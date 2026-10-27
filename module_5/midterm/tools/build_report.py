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
    arrow(drawing, [(321, 82), (359, 82)], "v2 proposal", (340, 91))
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
    story = []
    overall = evidence["overall"]
    by_name = {row["method"]: row for row in overall}
    frames = sum(row["processed_frames"] for row in videos)
    vectors = sum(row["sg4_vectors"] for row in videos)
    predicted_counts = Counter()
    for row in videos:
        predicted_counts.update(row["sg5_states"])
    assets = REPORT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    pipeline, decision, comparison = pipeline_diagram(), decision_diagram(), results_diagram(overall)
    for filename, drawing in (("connected_pipeline.svg", pipeline), ("decision_quality_flow.svg", decision),
                              ("controlled_comparison.svg", comparison)):
        renderSVG.drawToFile(drawing, str(assets / filename))

    # 1. Cover and executive summary.
    story += [p("CS477 COMPUTER VISION  |  SEECS CV FACE-OFF 2026", "eyebrow"),
              p("SG5 Drowsiness Decision<br/>and Alert Logic", "title"),
              p("Midterm technical report and integration handoff", "subtitle"),
              p("<b>Rafed Aftab</b> 457967 &nbsp;&nbsp; <b>Filza Umar</b> 464340<br/>"
                "G1-D2 Driver Drowsiness Monitoring &nbsp; | &nbsp; 28 October 2026"),
              Spacer(1, 7), p("Executive summary", "h2"),
              p("SG5 now has a reproducible, headless decision module connected to the available subgroup code. "
                "The PC pipeline runs SG1 face landmarks, SG2's selected EAR processor, a causal SG3 mouth adapter, "
                "the actual SG4 temporal engine, SG5 decision logic and the SG6 status-aware consumer. "
                "Five complete saved-video runs processed <b>" + str(frames) + " frames and " + str(vectors) +
                " temporal vectors</b>. Those clips have no independent drowsiness labels; their outputs establish "
                "interoperation, not detection accuracy."),
              p("The provisional primary is the robust C state machine; threshold A is the transparent backup. "
                "Five configurations were compared on the same 5,400 synthetic rows. Weighted B has the best "
                "overall sample accuracy but misses the short labelled episode. Robust C catches both episodes "
                "and fixes quality, timing and session handling; it is not the accuracy winner. "
                "The sensitivity candidate is retained for analysis rather than selected as a held-out winner."),
              p("The deliverable is a <b>PC-verified integration and SG6 software handoff</b>. SG3 calibration, "
                "SG4 adapter semantics and the proposed SG6 v2 fault policy need owner acceptance. "
                "Jetson boot, live camera delivery, GPIO operation and target performance are not verified here."),
              table(["Evidence boundary", "Status"], [
                  ["Connected source-to-request pipeline and reproducible comparisons", "Verified on PC"],
                  ["New adapter semantics and SG6 v2 contract", "Owner review pending"],
                  ["Real-driver accuracy and generalization", "Not established"],
                  ["Physical embedded operation", "SG6 target checks pending"],
              ], [350, WIDTH - 350]), Spacer(1, 10),
              p("Reading map", "h2"),
              p("2 Requirements and assessment evidence &nbsp; 3 Connected architecture &nbsp; "
                "4 Producer contracts &nbsp; 5 Decision logic &nbsp; 6 Controlled results &nbsp; "
                "7 Failure analysis &nbsp; 8 Real-video integration &nbsp; 9 SG6 handoff &nbsp; "
                "10 Reproduction and tests &nbsp; 11 GitHub and embedded readiness &nbsp; "
                "12 Remaining work and references", "small")]

    # 2. Rubric traceability.
    heading(story, 2, "Requirements and assessment evidence")
    story.append(p("The current Stage 1 assessment is <b>A 15 + B 10 + C 5 = 30 marks</b> [1]. "
                   "It is not the earlier Week 5 ten-mark subgroup rubric. The midterm permits a development-PC "
                   "prototype and does not require every algorithm to be deployed on Jetson. "
                   "This matrix maps evidence to the rubric; it does not assign marks."))
    rubric = [
        ["A", "7", "Working prototype: real SG4 replay, a complete saved-video pipeline, observable state/status and SG6 requests.", "PC verified"],
        ["A", "4", "Primary C and backup A; preserved B alternative; common-data tables, failure analysis and recovery sensitivity study.", "Evidence recorded"],
        ["A", "2", "SG4 v1.1 schema/golden parity; exact valid-only SG6 legacy adapter; explicit proposed v2 boundary and run commands.", "Technical checks pass; new semantics pending"],
        ["A", "2", "Unit/contract tests, strict metrics, no-face and silence tests; synthetic and unlabelled video limitations separated.", "PC verified"],
        ["B", "3", "Shared module structure; source snapshots and hashes; SG5 feature branch with separate integration additions.", "Review and merge are separate"],
        ["B", "3", "Existing private Project 2; assigned SG5 issues 8 and 9 plus midterm evidence/acceptance tracking.", "Team board evidence"],
        ["B", "2", "Module and SG6 READMEs, pinned PC dependencies, command sequence, examples, report and result links.", "Reproducible on PC"],
        ["B", "2", "Preserved 27 October SG4 alignment note, technical coordination register, owners and unresolved acceptance actions.", "No invented meeting or approvals"],
        ["C", "2", "Actual Jetson boot, storage and OS evidence must be shown by the team/SG6.", "Not verified by this work"],
        ["C", "1", "PC environment is pinned; SG6's reported detector-only target benchmark is separately attributed.", "Target stack needs confirmation"],
        ["C", "2", "Saved-video software path is tested; USB/CSI camera connection and target acquisition need SG6 evidence.", "Live target capture pending"],
    ]
    story.append(table(["Area", "Marks", "Demonstration evidence", "Qualification"], rubric,
                       [34, 38, 305, WIDTH - 377], small=True))
    story += [Spacer(1, 9), p("Delivery scope", "h2"),
              p("SG5 owns temporal-cue fusion and alert decisions, not the authorship of imported subgroup algorithms. "
                "The guide places multi-module integration at Lab 8, individual target deployment at Lab 9 and a complete "
                "embedded pipeline at Lab 11 [2]. The report supports the present gate and records what remains open.", "small")]

    # 3. Architecture and provenance.
    heading(story, 3, "Connected architecture and source provenance")
    story.append(p("One decoded frame feeds one SG1 detector. SG2 and SG3 share its landmarks and capture identity; "
                   "SG4 then aggregates synchronized evidence before SG5 decides. The old fixed-FPS SG4 notebook "
                   "was not used as the current integration target."))
    story.append(pipeline)
    caption(story, 1, "Implemented PC data path. SG3 and the availability gate are explicit adaptations; "
            "the final consumer emits hardware requests rather than operating a buzzer.")
    source_rows = []
    roles = {"SG1": "Actual face/landmark detector and validator", "SG2": "Selected EAR processor and cue adapter",
             "SG3": "Reference MAR indices and thresholds; new causal adapter", "SG4": "Actual timestamp-based TemporalEngine and goldens",
             "SG5": "Preserved Week 5 A/B/C reference algorithms", "SG6": "Legacy validator and reported target evidence"}
    for source in sources["sources"]:
        source_rows.append([source["subgroup"], text(source["branch"]),
                            "<font name='Courier'>" + source["commit"][:12] + "</font>", roles[source["subgroup"]]])
    story.append(table(["Owner", "Source branch", "Commit prefix", "Reused responsibility"], source_rows,
                       [44, 123, 96, WIDTH - 263], small=True))
    story.append(p("Full commits, original Git-blob SHA-256 hashes, import scopes and attribution are versioned in "
                   "<font name='Courier'>integration/sg5_midterm_sources.json</font>. "
                   "The current SG4 source is branch <b>saman</b>. Source import is not an assertion of human "
                   "review, acceptance or a main-branch merge.", "small"))

    # 4. Contracts and adapters.
    heading(story, 4, "Producer contracts and explicit adaptations")
    story.append(p("SG5 consumes SG4's current six-field v1.1 record without renaming its units or changing its "
                   "temporal windows. All five native producer streams retain exact golden-output parity."))
    story.append(table(["SG4 field", "Interpretation"], [
        ["time_s", "Increasing capture-clock seconds within one driver session"],
        ["face_valid", "Current face observation availability, 0 or 1"],
        ["perclos", "Valid eye-closed-time fraction, 0-1, in a 60-second window; not percent"],
        ["eye_closure_s", "Current ongoing eye-closure duration in seconds; zero when open/invalid"],
        ["long_blinks", "Closure-event count for durations at least 0.5 s, over 30 seconds"],
        ["yawn_count", "Debounced yawn-event count over 60 seconds, not yawn-frame count"],
    ], [118, WIDTH - 118]))
    story += [p("SG2 hard states are not probabilities", "h2"),
              p("The selected SG2 processor returns OPEN, CLOSED or UNKNOWN with explicit eye validity. "
                "Its closure probability and SG1's per-face detection confidence can be null. "
                "The narrow availability synchronizer preserves those absences instead of replacing them "
                "with thresholds or fabricated probabilities. SG4's actual window/event logic is retained. "
                "The first observation after a gap greater than 200 ms is censored in the annotated SG5 path, "
                "for both native and hard-state inputs, to break unsupported runs. Unannotated native replay retains reference behavior."),
              p("SG3 is a causal adaptation of the teammate experiment", "h2"),
              p("The source Colab script includes notebook commands and offline future-interval analysis; "
                "it cannot be imported as a live module unchanged. The portable adapter reuses mouth indices "
                "61, 291, 13, 14, 82, 87, 312 and 317. Coordinates are converted to pixels before distances are taken:"),
              code("MAR = mean(d(13,14), d(82,87), d(312,317)) / d(61,291)\n"
                   "pixel_x = normalized_x * image_width\n"
                   "pixel_y = normalized_y * image_height"),
              p("Inherited opening/hold thresholds are 0.50/0.45; confirmation requires 1.5 s. "
                "The raw active mouth-opening flag goes to SG4, which applies persistence/debounce once. "
                "The adapter's confirmed/event fields are diagnostics, not a second persistence input. "
                "Missing faces, invalid geometry or gaps reset continuity. Threshold calibration and owner acceptance remain open."),
              p("Quality is a separate observation property", "h2"),
              p("Direct integration carries current eye validity in addition to SG4's historical validity fraction. "
                "A visible face with unavailable eyes is not a usable current eye observation. These are "
                "SG5-side metadata, not silently added fields in the frozen SG4 wire schema. "
                "The measured CLOSED fraction is not independently validated P80 eyelid occlusion.")]

    # 5. Algorithm and state flow.
    heading(story, 5, "Decision logic and observation status")
    story.append(p("The core is rule-based and imports only the Python standard library. No SG5 model is trained. "
                   "The primary C design combines normalized evidence, an exponential smoother, hysteresis "
                   "and timestamp-based confirmation. State and observation status remain distinct."))
    story.append(decision)
    caption(story, 2, "Driver state is trusted only when status is OK. An insufficient or stale observation "
            "retains an untrusted state, suppresses a trusted drowsiness action and requests a sensor fault.")
    story.append(code("z_i = clip((x_i - low_i) / (high_i - low_i), 0, 1)\n"
                      "S = 0.45*z_perclos + 0.20*z_closure\n"
                      "  + 0.20*z_long_blinks + 0.15*z_yawns\n"
                      "M_t = M_previous + (1 - exp(-dt / 2.0)) * (S_t - M_previous)"))
    story.append(p("Normalization bounds (low, high): PERCLOS (0.05, 0.30), closure seconds (0.40, 2.00), "
                   "long-blink count (1, 6), and yawn count (0, 3). Values outside each range are clipped.", "small"))
    story.append(table(["Parameter", "Stable C default", "Purpose"], [
        ["WARNING entry / exit", "0.20 / 0.14", "Separate boundaries reduce threshold chatter"],
        ["DROWSY entry / exit", "0.65 / 0.53", "Different entry and release requirements"],
        ["Smoothing / entry confirmation", "2 s / 1 s", "Filter brief score changes; confirm the same higher target"],
        ["Lower-risk confirmation", "3 s", "Require continuous lower evidence at each release boundary"],
        ["Closure override", "1.5 s", "A valid prolonged closure bypasses score confirmation"],
        ["Quality floor / source gap", "0.55 / 0.5 s", "Reject unusable evidence and restart temporal support"],
    ], [146, 110, WIDTH - 256], small=True))
    story.append(p("There is no forced five-second NORMAL warm-up in the new core. Invalid observations reset "
                   "smoothing/confirmation; new sessions explicitly reset state. Duplicate, backward and nonfinite "
                   "timestamps are rejected. None of the engineering score weights is a learned probability.", "small"))

    # 6. Controlled quantitative comparison.
    heading(story, 6, "Controlled comparison on fixed development data")
    story.append(p("All five configurations receive identical six-field inputs from the two preserved synthetic "
                   "drives. The allowlist excludes ground-truth labels from every decision call. The original A/B/C "
                   "functions are extracted without GUI imports and remain unchanged; exact prediction parity "
                   "passes for 16,200 values across six drive-method comparisons."))
    story.append(table(["Development sequence", "Rows", "Duration", "Role"], [
        ["Drive 1", "3,000", "300 s", "Gradual drowsiness, short closure episode and recovery"],
        ["Drive 2", "2,400", "240 s", "Talking-related cues, tiredness, noise and face loss"],
    ], [125, 55, 68, WIDTH - 248]))
    story.append(Spacer(1, 8))
    labels = {"week5_A": "A reference", "week5_B": "B reference", "week5_C": "C reference",
              "stable_c": "C robust", "c_fast_recovery": "C fast recovery"}
    rows = []
    for item in overall:
        event = item["events"]
        rows.append([labels[item["method"]], pct(item["accuracy"]), f"{item['macro_f1']:.3f}",
                     f"{event['detected_events']}/{event['ground_truth_events']}", str(event["false_alert_events"]),
                     f"{item['false_drowsy_duration_s']:.1f}", str(item["driver_state_changes"]),
                     "n/a" if event["mean_latency_s"] is None else f"{event['mean_latency_s']:.2f}"])
    story.append(table(["Configuration", "Accuracy", "Macro F1", "Events caught", "Unmatched onsets",
                        "False D time s", "Driver changes", "Delay s"], rows,
                       [104, 56, 48, 48, 65, 61, 66, WIDTH - 448], small=True))
    story.append(p("Pooled metrics weight samples and matched events rather than averaging per-drive percentages. "
                   "Unavailable outputs remain UNKNOWN errors in the denominator. Rates are synthetic-development "
                   "results, not real-driver accuracy. The raw driver-state changes above exclude status transitions.", "caption"))
    story.append(comparison)
    caption(story, 3, "Higher macro F1 and lower false-DROWSY duration favor different configurations; "
            "the faster candidate is a sensitivity study, not an independently selected winner.")
    story.append(p("The actual SG4 implementation uses a <b>60-second</b> PERCLOS window; these legacy synthetic "
                   "drives use <b>30 seconds</b>. The identical field name does not establish matching input "
                   "distributions. Real SG4 thresholds must be re-evaluated on independent labelled recordings.", "small"))

    # 7. Metric definitions and failure analysis.
    heading(story, 7, "Failure analysis and selection rationale")
    story.append(p("<b>Primary: robust C. Backup: threshold A.</b> C is retained for explicit observation quality, "
                   "correct time/session handling and interpretable state transitions, not as an accuracy improvement. "
                   "A is a low-complexity, transparent fallback. B remains an implemented comparison and has the "
                   "highest pooled sample accuracy on this development set."))
    story.append(table(["Finding", "Evidence", "Engineering implication"], [
        ["B misses the short episode", "One of two episodes detected; eye closure alone contributes at most 0.20 to a 0.50 DROWSY threshold.", "Keep an explicit prolonged-closure rule rather than relying only on the blended score."],
        ["A fragments a longer episode", "22 native state changes; strict one-to-one evaluation leaves a repeated onset unmatched.", "Threshold crossings need temporal confirmation and a documented alert repetition policy."],
        ["C delays gradual detection and recovery", "Strict mean delay 11.60 s for robust C; false-DROWSY overhang 8.7 s.", "Collect labelled real streams; tune smoothing and release against latency and missed-duration costs."],
        ["Faster recovery trades recall for overhang", "False-DROWSY time falls to 0.0 s but DROWSY sample recall drops.", "Do not choose a winner solely because one development metric improves."],
    ], [112, 202, WIDTH - 314], small=True))
    stable = by_name["stable_c"]
    story.append(p("Robust C sample performance", "h2"))
    story.append(table(["Reference class", "Support", "Precision", "Recall", "F1"], [
        [state, str(stable["per_class"][state]["support"]),
         f"{stable['per_class'][state]['precision']:.3f}", f"{stable['per_class'][state]['recall']:.3f}",
         f"{stable['per_class'][state]['f1']:.3f}"] for state in ("NORMAL", "WARNING", "DROWSY")],
        [145, 75, 95, 95, WIDTH - 410]))
    story += [p("Strict metrics are not interchangeable with the old scores", "h2"),
              p("A detected event requires a <b>new predicted DROWSY onset inside its labelled half-open interval</b>, "
                "one-to-one. Preexisting overlap is recorded separately as coverage; it does not create a negative "
                "latency. Late onsets after unused episodes are diagnostic only. No detected event means null delay, "
                "not zero. False-DROWSY duration counts time spent DROWSY outside the labelled DROWSY state."),
              p("The original evaluator allowed many-to-one overlap and a five-second post-episode grace. "
                "A's two unmatched onsets here include one repeated onset and one late onset after an already detected "
                "episode. They are not evidence that A's unchanged algorithm suddenly produced two unrelated false incidents."),
              p("Robust C has <b>11 native driver-state changes and 16 availability-status changes</b>; the evaluated "
                "prediction trace therefore changes 27 times when non-OK status becomes UNKNOWN. It is misleading "
                "to label all 27 changes as driver-state flicker. Macro F1 is averaged over three target classes; "
                "UNKNOWN remains a prediction column and an error, not a fourth ground-truth class.", "small")]

    # 8. Real video evidence.
    heading(story, 8, "Connected execution on five saved videos")
    story.append(p(f"The complete PC path processed <b>{frames:,} source frames and {vectors:,} SG4 vectors</b>. "
                   f"All {vectors:,} decisions had status OK and passed the usable legacy structural adapter. "
                   f"The output contained {predicted_counts.get('NORMAL', 0)} NORMAL and "
                   f"{predicted_counts.get('WARNING', 0)} WARNING predictions; no DROWSY prediction occurred. "
                   "These counts are observations of the software, not validated driver states."))
    rows = []
    for index, video in enumerate(videos, 1):
        rows.append([f"Clip {index:02d}", str(video["processed_frames"]), str(video["sg4_vectors"]),
                     f"{video['mean_pipeline_processing_ms']:.2f}", f"{video['p95_pipeline_processing_ms']:.2f}",
                     f"{video['offline_throughput_fps_including_io']:.2f}"])
    story.append(table(["SG1 source", "Frames", "Vectors", "Mean process ms", "p95 process ms", "Offline fps"],
                       rows, [90, 65, 65, 95, 95, WIDTH - 410]))
    story.append(p("Processing time excludes acquisition and annotation/encoding. Offline throughput includes file I/O. "
                   "Neither is a live-camera or Jetson FPS measurement. The five runs used Windows Python 3.11.0, "
                   "NumPy 1.26.4, OpenCV 4.11.0 and MediaPipe 0.10.21; SG5 was evaluated approximately at 10 Hz.", "caption"))
    example = RESULTS / "video01" / "example_warning.jpg"
    if example.exists():
        story.append(Image(str(example), width=WIDTH, height=WIDTH * 1080 / 2280))
        caption(story, 4, "Saved Clip 01 observation at 26.40 s: actual SG1 face geometry, SG2 OPEN, "
                "SG3 MAR 0.019 and SG5 WARNING with status OK. A state can reflect historical cues even "
                "when the mouth is currently closed. The screenshot is an output example, not a ground-truth label.")
    story += [p("What this run establishes", "h2"),
              p("The source-to-consumer path executes without inventing confidence values or dropping source identity. "
                "Per-stage JSONL, source/model hashes, timings, example packets and annotated MP4s are available "
                "under each <font name='Courier'>results/videoNN</font> directory. Full source clips originate in SG1's branch."),
              p("Independent drowsiness, yawn and eye-event annotations were unavailable for these clips. "
                "No real-video precision, recall or accuracy is claimed. The SG3 segment counts are predictions. "
                "No DROWSY output here does not prove that all subjects were awake or that the system has high recall.", "small")]

    # 9. SG6 payload and lifecycle.
    heading(story, 9, "SG6 software handoff and fault behavior")
    story.append(p("The proposed <font name='Courier'>sg5.sg6.v2</font> packet has fourteen fields, strict types "
                   "and explicit status. SG6's dry-run consumer validates each packet and produces idempotent requests. "
                   "It has no camera, GPIO, network or sound side effects."))
    story.append(table(["Packet fields", "Meaning"], [
        ["schema_version; time_s; session_id", "Version and source capture identity"],
        ["driver_state; status", "Retained NORMAL/WARNING/DROWSY, usable only while status is OK"],
        ["score; smoothed_score; quality", "Engineering evidence and observed quality, not trained probabilities"],
        ["alert; alert_level; alert_event", "Actionable state, level 0/1/2, and one-shot upward transition"],
        ["transition; reason; config_id", "Native state change, explanation and versioned rules"],
    ], [225, WIDTH - 225]))
    packet = None
    with (RESULTS / "demo_drowsy" / "sg6_stream.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            candidate = json.loads(line)
            if candidate["driver_state"] == "DROWSY" and candidate["status"] == "OK":
                packet = candidate
                break
    if packet is not None:
        story += [p("Actual saved prolonged-closure decision", "h2"), code(json.dumps(packet, indent=2))]
    story.append(table(["Condition", "Hardware request"], [
        ["OK + WARNING", "visual_warning = true; no DROWSY buzzer request"],
        ["OK + DROWSY", "visual_warning = true; buzzer_requested = true"],
        ["INSUFFICIENT_EVIDENCE or STALE", "sensor_fault = true; no trusted drowsiness request"],
    ], [225, WIDTH - 225]))
    story.append(p("The exact legacy adapter returns only driver_state, alert and confidence for usable decisions; "
                   "legacy confidence means observation quality. It raises for insufficient/stale observations. "
                   "SG6's actual old validator accepts this shape. That proves structural compatibility, not acceptance "
                   "of a new semantic policy. SG6 still owns alarm repetition, fault indication and physical wiring.", "small"))

    # 10. Tests and runbook.
    heading(story, 10, "Verification and reproducible demonstration")
    story.append(p("Run from the repository root using the isolated Windows Python 3.11 environment. "
                   "The decision core and consumer are standard-library-only; real SG4 replay needs the core requirements. "
                   "The full vision path uses the validated PC pins. It does not require a Torch/CNN checkpoint in selected EAR mode."))
    story.append(code("python -m venv .venv\n"
                      ".\\.venv\\Scripts\\python.exe -m pip install -r module_5/midterm/requirements-pc.txt\n"
                      ".\\.venv\\Scripts\\python.exe module_1/scripts/download_model.py"))
    story.append(p("Create the environment only if absent. The SG1 downloader checks the official model SHA-256. "
                   "This uses a pretrained landmark model [5]; neither landmark training nor SG5 model training is performed.", "small"))
    story.append(code('$py = ".\\.venv\\Scripts\\python.exe"\n'
                      '& $py -m module_5.midterm.demo --scenario drowsy\n'
                      '& $py -m module_5.midterm.demo --scenario face_lost\n'
                      '& $py -m module_5.midterm.evaluate --plot\n'
                      '& $py -m unittest discover -s module_5/midterm/tests -v\n'
                      '& $py -m module_5.midterm.pipeline `\n'
                      '  --video module_1/data/videos/driver_sample_01.mp4 `\n'
                      '  --output module_5/midterm/results/video01 --annotated'))
    story.append(p("Use the full output/consumer command sequence in <font name='Courier'>module_5/midterm/scripts.md</font>. "
                   "The mock demo executes the actual SG4 engine; the vision command executes actual upstream "
                   "inference. Those are intentionally separate demonstrations. Plots are headless and saved as PNGs."))
    story.append(table(["Verification layer", "What the check establishes"], [
        ["SG5 decisions and contracts", "State timing, target-specific confirmation, invalid quality, current-eye availability, session/gap reset, strict schemas, legacy compatibility and silent delivery faults"],
        ["SG3 geometry and temporal logic", "Pixel MAR on rectangular frames, causal opening/hold behavior, one diagnostic event per confirmation, identity/time preservation and invalid-input reset"],
        ["SG4 conformance", "All five producer goldens match; actual SG4 vectors pass the v1.1 contract and run through SG5/SG6"],
        ["Original baseline and metrics", "Exact A/B/C parity, no label leakage, one-to-one episode matching, nonnegative latency, explicit UNKNOWN errors and separate status changes"],
        ["Upstream regression", "SG1/SG4 and SG2 tests are executed separately in compatible environments; upstream code remains attributed and unchanged"],
    ], [150, WIDTH - 150], small=True))
    if verification:
        total_tests = verification.get("total_passing_tests")
        suites = [str(check["test_count"]) for check in verification.get("checks", [])
                  if check.get("test_count") is not None]
        counts = ", ".join(suites)
        story.append(p(f"<b>Recorded software verification: {total_tests} passing tests</b> "
                       f"across the SG5, SG1/SG4 and SG2 suites ({counts}, respectively). "
                       "SG2 regression uses the separate existing Torch environment; it is not a universal "
                       "vision-environment claim. Dependency consistency also passed. "
                       "Machine-readable commands, outputs and run evidence are recorded in "
                       "<font name='Courier'>module_5/midterm/results/verification.json</font>. "
                       "These are software checks, not target-hardware validation.", "small"))
    story.append(p("Producer tick uses the capture clock; transport silence uses SG6's independent monotonic-arrival "
                   "watchdog. The live hardware loop must poll while no messages arrive. A file/stdin replay is "
                   "not itself a continuously polling hardware watchdog.", "small"))

    # 11. GitHub and embedded readiness.
    heading(story, 11, "GitHub governance and embedded readiness")
    branch_url = GITHUB + "/tree/" + BRANCH
    story += [p(f"Shared repository: <link href='{GITHUB}' color='#245D83'>Sananismm/CV_Drowsinees_Detection</link><br/>"
                f"Integration branch: <link href='{branch_url}' color='#245D83'>{BRANCH}</link><br/>"
                f"Team board: <link href='{BOARD}' color='#245D83'>Computer-Vision Driver Drowsiness Monitoring, Project 2</link> "
                "(private; team access required).")]
    if pr_url:
        story.append(p(f"Review request: <link href='{text(pr_url)}' color='#245D83'>{text(pr_url)}</link>. "
                       "Opening a review request does not establish reviewed acceptance or a main merge."))
    story.append(p("The first <link href='https://github.com/Sananismm/CV_Drowsinees_Detection/actions/runs/40592451184' "
                   "color='#245D83'>Linux GitHub Actions software check passed</link> for implementation commit "
                   "<font name='Courier'>8ab3e2334009</font>. CI verifies software checks, not the physical target.", "small"))
    story.append(table(["Tracked work", "Evidence and next decision"], [
        ["Issue 8", "Named warning-threshold / 1.5-second recovery sensitivity candidate and common-data comparison; review the trade-offs before closing."],
        ["Issue 9", "Current SG4 implementation and native schema/goldens are used; connected PC runs exist. New adapter semantics still need owner review."],
        ["Issue 19", "Midterm report, reproducibility and test evidence; link the recorded run and review request rather than marking completion from file creation alone."],
        ["Issue 20", "SG3/SG4/SG6 acceptance and target-hardware checks remain distinct unresolved work."],
    ], [110, WIDTH - 110]))
    story.append(p("The existing 27 October SG4 alignment note is retained without inventing SG5 attendance or "
                   "new approval. The coordination register records producer/consumer responsibilities and unresolved "
                   "decisions. Imported algorithm work is credited to its original subgroup; both SG5 members must "
                   "explain their genuine contribution rather than treating assigned ownership as proof of authorship."))
    story.append(p("Embedded platform evidence has a separate boundary", "h2"))
    story.append(table(["Stage 1 C criterion", "Current evidence and remaining action"], [
        ["Boot and environment  2 marks", "SG6 must show actual Jetson Orin Nano 8GB boot, storage and OS. This preparation did not access the device."],
        ["Development stack  1 mark", "PC pins and standard-library core are reproducible. Confirm ARM64 runtime compatibility, detailed landmarks and required software on the actual target."],
        ["Camera readiness  2 marks", "Saved videos verify the software path only. SG6 must demonstrate USB/CSI capture or document the actual acquisition blocker."],
    ], [172, WIDTH - 172]))
    story.append(p("SG6's inherited detector benchmark <b>reports</b> Haar 31.65 ms and YuNet 17.89 ms mean inference "
                   "on 150 private recorded frames. It was not rerun here, excludes acquisition and SG2-SG5, and "
                   "cannot be used as this pipeline's Jetson result. YuNet's five keypoints do not supply SG2's "
                   "detailed eye landmarks. Physical camera, GPIO, target latency and memory remain unverified.", "small"))
    story.append(code('& $py embedded_6/sg5_handoff/check_platform.py `\n'
                      '  --output module_5/midterm/results/platform_pc.json'))
    story.append(p("The recorded PC probe identifies Windows, not Jetson, and opens no camera by default. "
                   "SG6 can run the same collector on its device, explicitly choosing --camera for a physical "
                   "capture test. A video fallback cannot prove a connected camera.", "small"))

    # 12. Limitations, next actions and references.
    heading(story, 12, "Remaining work and references")
    story.append(table(["Priority", "Owner action and completion evidence"], [
        ["Interface acceptance", "SG3 reviews causal pixel MAR and thresholds; SG4 reviews hard-state availability/gap behavior; SG6 reviews v2 status and fault requests. Record explicit decisions and tests."],
        ["Independent validation", "Collect independently labelled real SG4 streams. Split development from evaluation subjects/clips; compare event recall, false duration, delay and coverage with the same protocol."],
        ["Target bring-up", "SG6 records boot, exact runtime/model versions, camera capture and the hardware policy. Test no face, stopped producer and broken delivery before enabling physical alerts."],
        ["Profiling and next gate", "Measure end-to-end acquisition/decision latency, throughput and memory on Jetson. Treat the present PC numbers as development measurements only."],
    ], [123, WIDTH - 123], small=True))
    story += [p("Known limitations", "h2"),
              p("The two synthetic drives are a small development set, and their PERCLOS window differs from the real "
                "producer. Five unlabelled video runs establish execution, not drowsiness accuracy or safe real-driving "
                "operation. MAR and EAR thresholds remain person/pose/lighting-sensitive. No independent P80 "
                "occlusion measurement, calibrated drowsiness probability or head-nod detector is claimed. "
                "A stopped or invalid sensor cannot establish an awake driver. Human interface acceptance and "
                "physical target validation remain required even when PC tests pass."),
              p("References and evidence locations", "h2"),
              p("[1] CS477. <i>Midterm Project Evaluation Stage 1</i>, Week 8, pp. 1-2. "
                "Assessment authority for the current A15/B10/C5 scope and evidence boundary.", "small"),
              p("[2] CS477. <i>SEECS CV Face-Off 2026 Semester Project Guide</i>, pp. 3-7. "
                "SG5 role, interface-first development, accountability and Lab 8/9/11 integration gates.", "small"),
              p("[3] CS477. <i>Week 5 Subgroup Tasks GitHub Readiness Assessment</i>, pp. 1-3 and 6. "
                "Preserved baseline, controlled alternatives, common metrics and separate decision/UI responsibility.", "small"),
              p("[4] CS477. <i>Semester Project Topic Sub Group Allocations Section A B</i>, p. 2, rows 48-49. "
                "G1-D2 SG5 membership and student identifiers.", "small"),
              p("[5] Google AI Edge. <i>Face landmark detection guide for Python</i>. "
                "<link href='https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python' "
                "color='#245D83'>Official MediaPipe documentation</link>, accessed 28 October 2026. "
                "Pretrained landmark inference and timestamped video API, not an SG5 training claim.", "small"),
              p("[6] Team repository snapshots and full hashes: <font name='Courier'>integration/sg5_midterm_sources.json</font>. "
                "Controlled evidence: <font name='Courier'>module_5/midterm/results/evaluation/evaluation.json</font>. "
                "Connected evidence: <font name='Courier'>module_5/midterm/results/video01</font> through "
                "<font name='Courier'>video05</font>, each with its own summary, source/model hashes and stream outputs.", "small"),
              p("<b>Handoff conclusion.</b> SG5 has a reproducible PC integration and a strictly validated software "
                "consumer boundary for SG6 review. The report does not substitute for owner approval, independent "
                "real-driver evaluation or the team's physical embedded-readiness demonstration.")]
    return story


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT / "SG5_Midterm_Report.pdf")
    parser.add_argument("--render-dir", type=Path, help="Optional QA PNG directory; not a submission artifact")
    parser.add_argument("--pr-url", help="Published team review request URL, when available")
    args = parser.parse_args(argv)
    evidence = load_json(RESULTS / "evaluation" / "evaluation.json")
    videos = [load_json(RESULTS / f"video{i:02d}" / "summary.json") for i in range(1, 6)]
    sources = load_json(REPOSITORY / "integration" / "sg5_midterm_sources.json")
    verification_path = RESULTS / "verification.json"
    verification = load_json(verification_path) if verification_path.exists() else None
    if args.pr_url is None and verification:
        args.pr_url = verification.get("pull_request")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(args.output), pagesize=A4, leftMargin=46, rightMargin=46,
                                topMargin=40, bottomMargin=43, title="SG5 Drowsiness Decision and Alert Logic",
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
