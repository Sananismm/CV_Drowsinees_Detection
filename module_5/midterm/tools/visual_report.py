"""Results-first eight-page report; evidence is pinned, not taken from practice reruns."""

import hashlib
import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.platypus import Flowable, Image, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.utils import ImageReader


def asset_hash(path):
    data = path.read_bytes()
    if path.suffix in {".json", ".jsonl", ".txt", ".svg"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


class Photo(Flowable):
    """Crop a source photo only in the PDF viewport; never stretch geometry."""

    def __init__(self, path, width, height, cover=True):
        super().__init__()
        self.path, self.width, self.height, self.cover = str(path), width, height, cover

    def draw(self):
        source = ImageReader(self.path)
        iw, ih = source.getSize()
        scale = max(self.width/iw, self.height/ih) if self.cover else min(self.width/iw, self.height/ih)
        w, h = iw*scale, ih*scale
        canvas = self.canv
        canvas.saveState()
        clip = canvas.beginPath()
        clip.rect(0, 0, self.width, self.height)
        canvas.clipPath(clip, stroke=0)
        canvas.drawImage(source, (self.width-w)/2, (self.height-h)/2, w, h)
        canvas.restoreState()


def metric_cards(values, width, ink, pale):
    drawing = Drawing(width, 58)
    gap = 9
    cell = (width-gap*(len(values)-1))/len(values)
    for i, (number, label) in enumerate(values):
        x = i*(cell+gap)
        drawing.add(Rect(x, 3, cell, 51, rx=4, ry=4, fillColor=pale, strokeColor=None))
        drawing.add(String(x+cell/2, 28, str(number), fontName="Helvetica-Bold", fontSize=21, fillColor=ink, textAnchor="middle"))
        drawing.add(String(x+cell/2, 12, label, fontName="Helvetica", fontSize=8.1, fillColor=ink, textAnchor="middle"))
    return drawing


def evidence_map(layout):
    width, blue, pale, ink = (layout[x] for x in ("WIDTH", "BLUE", "PALE", "INK"))
    drawing = Drawing(width, 139)
    rows = [(96, "2 synthetic temporal drives", "5,400 labelled rows", "Compare decision methods", "Accuracy, F1, events, delay"),
            (49, "SG4 mock frame cues", "Actual TemporalEngine executes", "Repeatable alert / fault demos", "State changes and hardware requests"),
            (2, "5 actual SG1 video clips", "2,932 image frames", "Connected software execution", "No independent accuracy labels")]
    for y, source, detail, target, outcome in rows:
        for x, w, title, subtitle in ((0, 215, source, detail), (253, width-253, target, outcome)):
            drawing.add(Rect(x, y, w, 39, rx=4, ry=4, fillColor=pale, strokeColor=colors.HexColor("#CBD5E0"), strokeWidth=.6))
            drawing.add(String(x+w/2, y+24, title, fontName="Helvetica-Bold", fontSize=8.7, fillColor=blue, textAnchor="middle"))
            drawing.add(String(x+w/2, y+10, subtitle, fontName="Helvetica", fontSize=8.1, fillColor=ink, textAnchor="middle"))
        layout["arrow"](drawing, [(215,y+20),(253,y+20)])
    return drawing


def action_map(layout):
    width, blue, ink, pale = (layout[x] for x in ("WIDTH", "BLUE", "INK", "PALE"))
    drawing = Drawing(width, 166)
    rows = [(124, "OK + NORMAL", "No warning request", "#E9F2F5"),
            (84, "OK + WARNING", "Visual warning", "#FFF3D7"),
            (44, "OK + DROWSY", "Visual + buzzer request", "#F7E1DE"),
            (4, "INSUFFICIENT / STALE", "Sensor fault; retained state is untrusted", "#FCF0DF")]
    for y, state, request, fill in rows:
        for x, w, label in ((0, 188, state), (234, width-234, request)):
            drawing.add(Rect(x, y, w, 31, rx=4, ry=4, fillColor=colors.HexColor(fill), strokeColor=None))
            drawing.add(String(x+w/2, y+12, label, fontName="Helvetica-Bold" if x==0 else "Helvetica", fontSize=8.5, fillColor=ink, textAnchor="middle"))
        layout["arrow"](drawing, [(188,y+15),(234,y+15)])
    return drawing


def weight_bar(layout):
    drawing = Drawing(layout["WIDTH"], 32)
    x = 0
    for share, label, fill in ((.45,"PERCLOS 45%","#D5E7F4"),(.20,"Closure 20%","#DAEDE9"),(.20,"Long blinks 20%","#E4DFF2"),(.15,"Yawns 15%","#F2E1E8")):
        w = share*layout["WIDTH"]
        drawing.add(Rect(x, 2, w, 28, fillColor=colors.HexColor(fill), strokeColor=colors.white))
        drawing.add(String(x+w/2, 12, label, fontName="Helvetica-Bold", fontSize=8.1, fillColor=layout["INK"], textAnchor="middle"))
        x += w
    return drawing


def build_story(evidence, videos, sources, verification=None, pr_url=None, *, layout):
    # The visual edition intentionally uses full-run snapshots, even when a user
    # has since stopped an interactive run early or regenerated timing outputs.
    root = layout["REPOSITORY"]
    assets = layout["REPORT"] / "assets"
    bundle = json.loads((assets / "evidence_bundle.json").read_text(encoding="utf-8"))
    evidence, videos, verification = (bundle[x] for x in ("evaluation", "videos", "verification"))
    width = layout["WIDTH"]
    p, table, code = (layout[x] for x in ("p", "table", "code"))
    heading = layout["heading"]
    styles = layout["STYLES"]
    styles["body"].fontSize, styles["body"].leading = 10.2, 14.1
    styles["small"].fontSize, styles["small"].leading = 8.7, 12
    styles["cell"].fontSize, styles["cell"].leading = 8.7, 11.7
    story = []
    overall = evidence["overall"]
    primary = next(r for r in overall if r["method"] == "stable_c")
    total_frames = sum(v["processed_frames"] for v in videos)
    total_vectors = sum(v["sg4_vectors"] for v in videos)

    def picture(name, w=width, max_height=1000):
        path = assets / name
        with PILImage.open(path) as image:
            iw, ih = image.size
        h = w*ih/iw
        if h > max_height:
            w *= max_height/h
            h = max_height
        return Image(str(path), width=w, height=h)

    def cap(text):
        story.append(p(text,"caption"))

    def cards(values):
        story.append(metric_cards(values,width,layout["INK"],layout["PALE"]))
        story.append(Spacer(1,5))

    def pair(left,right,gap=13):
        item=Table([[left,"",right]],colWidths=[(width-gap)/2,gap,(width-gap)/2])
        item.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
        story.append(item)

    # 1. Results, not a separate decorative cover page.
    story += [p("CS477 COMPUTER VISION  |  G1-D2  |  28 OCTOBER 2026","eyebrow"),
              p("SG5 Midterm Results","title"),
              p("Drowsiness Decision and Alert Logic","subtitle"),
              p("<b>Rafed Aftab 457967</b> &nbsp; <b>Filza Umar 464340</b>","body")]
    cards([(f"{verification['total_passing_tests']:,}","recorded passing tests"),("5,400","labelled synthetic rows"),(f"{total_frames:,}","actual video frames"),(f"{total_vectors:,}","SG6 decision packets")])
    story.append(p("<b>Result:</b> the connected PC pipeline executes. Robust C is the provisional primary; A is the backup. C is <b>not</b> the accuracy winner.","body"))
    story.append(picture("video03_output.jpg",max_height=240))
    cap("Actual annotated output from shared Clip 03. The face and measurements are observed video evidence; the displayed driver state is a prediction, not an independent label.")
    story.append(evidence_map(layout))
    cap("Figure 1. Three evidence sources answer three different questions. None is a training dataset for SG5.")
    story.append(p("<b>Verified on PC:</b> source-to-request execution and software contracts. <b>Still open:</b> adapter acceptance, independent real-driver validation and physical Jetson/camera/GPIO checks.","small"))

    # 2. Retain the structured architecture, compress the explanation.
    heading(story,2,"Connected pipeline and decision rules")
    story.append(layout["pipeline_diagram"]())
    cap("Figure 2. Shared frames and timestamps connect the subgroup pipeline. SG3 and the availability gate are explicit adapters. The proposed SG6 v2 emits requests without operating hardware.")
    story.append(table(["SG4 input","Unit / window"],[
        ["time_s; face_valid","Capture seconds; current face availability"],
        ["perclos; eye_closure_s","Closed-eye fraction over 60 s; ongoing closure seconds"],
        ["long_blinks; yawn_count","Closure events over 30 s; yawn events over 60 s"],
    ],[width*.43,width*.57]))
    story += [Spacer(1,9),p("Weighted, normalized evidence","h2"),weight_bar(layout)]
    story.append(table(["Stable C setting","Value"],[
        ["WARNING entry / exit","0.20 / 0.14"],
        ["DROWSY entry / exit","0.65 / 0.53"],
        ["EMA time constant / upward confirmation / recovery","2 s / 1 s / 3 s"],
        ["Prolonged-closure override / quality floor","1.5 s / 0.55"],
    ],[width*.64,width*.36]))
    cap("Scores use normalized cues, not raw seconds/counts or learned probabilities. Missing evidence breaks confirmation. Capture and delivery watchdogs use separate clocks.")

    # 3. Photographic evidence of actual feature processing.
    heading(story,3,"What the vision modules actually observed")
    story.append(p("Shared Clip 02: actual source-frame crops with their recorded SG2/SG3 outputs. These are illustrative predictions, not manually confirmed eye/yawn labels.","body"))
    signals = bundle["signal_photos"]
    titles = ["SG2 predicted OPEN","SG2 predicted CLOSED","SG3 low mouth-opening cue","SG3 active mouth-opening cue"]
    cells=[]
    cell_width=(width-13)/2
    for index,signal in enumerate(signals):
        value = f"EAR {signal['ear']:.3f}" if index<2 else f"MAR {signal['mar']:.3f}; active={str(signal['yawn_active']).lower()}"
        cells.append([p(titles[index],"h2"),Photo(assets/signal["asset"],cell_width,147),p(f"Frame {signal['frame_id']} | {signal['time_s']:.2f} s | {value}","small")])
    pair(cells[0],cells[1])
    story.append(Spacer(1,6))
    pair(cells[2],cells[3])
    story.append(Spacer(1,5))
    story.append(picture("recorded_eye_mouth_signals.png",max_height=140))
    cap("Figure 3. Recorded EAR and MAR signals from the same clip. Dashed rules: EAR 0.15 and MAR opening 0.50; dotted MAR hold 0.45. Mouth opening alone is not a confirmed yawn; SG4 applies duration/debounce.")

    # 4. Comparison is the central result, not a long methodological narrative.
    heading(story,4,"Controlled comparison")
    story.append(p("Five configurations; identical 5,400 synthetic rows. Labels are excluded from every decision call. Original A/B/C parity passes for all 16,200 saved predictions.","body"))
    rows=[]
    for label,row in zip(["A reference","B reference","C original","C robust","C fast recovery"],overall):
        event=row["events"]
        rows.append([label,f"{100*row['accuracy']:.1f}%",f"{row['macro_f1']:.3f}",f"{event['detected_events']}/{event['ground_truth_events']}",str(row['driver_state_changes']),f"{row['false_drowsy_duration_s']:.1f}",f"{event['mean_latency_s']:.2f}"])
    story.append(table(["Configuration","Accuracy","Macro F1","Caught","Changes","False D s","Delay s"],rows,[108,67,65,52,60,74,width-426]))
    story.append(Spacer(1,10))
    story.append(picture("results_dashboard.png",max_height=310))
    cap("Figure 4. Synthetic development results. 'Changes' excludes observation-status transitions; false D time is time predicted DROWSY outside labelled DROWSY intervals.")
    story.append(p("<b>B:</b> highest accuracy, but misses the short episode. <b>C robust:</b> catches both episodes with 11 native state changes. <b>C fast:</b> overhang falls to 0 s, but DROWSY recall falls from 69.8% to 63.3%.","body"))
    cap("The CSV generator uses a 30-second PERCLOS window; actual SG4 uses 60 seconds. These scores do not validate real-stream thresholds or generalization.")

    # 5. Show the failure, not just say there is one.
    heading(story,5,"Detection timing and failure cases")
    story.append(picture("decision_timeline.png",max_height=300))
    cap("Figure 5. Drive 1: dashed lines show the reference. Pink bands mark labelled DROWSY periods; grey gaps mark unavailable predictions. N/W/D denote the three driver states.")
    story.append(picture("episode_zoom.png",max_height=122))
    cap("Figure 6. Filled segments are DROWSY predictions. B misses the short episode; C responds later to gradual drowsiness.")
    delays=primary["events"]["latencies_s"]
    cards([(f"{delays[0]:.1f} s","C short-episode delay"),(f"{delays[1]:.1f} s","C gradual-episode delay"),(f"{primary['events']['mean_latency_s']:.1f} s","C mean matched delay")])
    story.append(p("A detection requires a new DROWSY onset <b>inside</b> a labelled episode, one-to-one. Pre-existing overlap is coverage, not a negative delay. Misses have no latency value.","small"))
    story.append(p("<b>Selection:</b> keep robust C for interpretable temporal and missing-data behavior, with A as backup. Faster recovery is a sensitivity study, not a winner selected on independent data.","body"))

    # 6. Actual screenshots, five clips, concise performance evidence.
    heading(story,6,"Five complete saved-video demonstrations")
    rows=[]
    for i,run in enumerate(videos,1):
        rows.append([f"Clip {i:02d}",str(run["processed_frames"]),str(run["sg4_vectors"]),f"{run['mean_pipeline_processing_ms']:.2f}",f"{run['p95_pipeline_processing_ms']:.2f}"])
    story.append(table(["Source","Frames","Packets","Mean process ms","p95 process ms"],rows,[80,75,75,137,width-367]))
    story.append(Spacer(1,9))
    story.append(picture("video01_output.jpg",max_height=240))
    cap("Figure 7. Actual Clip 01 output at 26.40 s: SG2 OPEN, MAR 0.019, SG5 WARNING. A temporal decision can reflect earlier cues even when the mouth is now closed.")
    thumbnails=[]
    for i in range(2,6):
        thumbnails.append([Photo(assets/f"video{i:02d}_output.jpg",(width-24)/4,62,cover=False),p(f"Clip {i:02d}","small")])
    strip=Table([thumbnails],colWidths=[width/4]*4)
    strip.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(strip)
    cap("Figure 8. Recorded annotated outputs from the other four clips. All photographs originate from the shared SG1 videos.")
    normal=sum(v["sg5_states"].get("NORMAL",0) for v in videos)
    warning=sum(v["sg5_states"].get("WARNING",0) for v in videos)
    story.append(p(f"<b>{total_vectors:,} usable packets:</b> {normal} NORMAL, {warning} WARNING and no DROWSY predictions. No independent labels exist for these clips, so no detection accuracy is claimed.","body"))
    cap("PC processing excludes acquisition and annotation/encoding. These are Windows CPU measurements, not live-camera or Jetson FPS. Full-run snapshots are pinned at bf15c3b; later partial practice runs are not substituted.")

    # 7. Reproducible controlled output, explicitly not physical hardware.
    heading(story,7,"Alert and sensor-fault demonstrations")
    story.append(picture("demo_drowsy.png",max_height=112))
    cap("Figure 9. Actual SG4-to-SG5 mock replay, captured again for this report. Console text is rendered for legibility; times are scenario timestamps, not wall-clock waiting time.")
    story.append(picture("demo_face_lost.png",max_height=112))
    cap("Figure 10. Face loss at 15.0 s makes the retained NORMAL state untrusted. Recovery at 19.0 s restores usable observation status.")
    drawing=action_map(layout)
    story.append(drawing)
    renderSVG.drawToFile(drawing,str(assets/"sg6_action_map.svg"))
    cap("Figure 11. Validated SG6 software requests. No GPIO, physical buzzer or camera side effects occur in the consumer.")
    selected=next(d for d in bundle["demos"]["drowsy"]["example_decisions"] if d["driver_state"]=="DROWSY")
    story.append(table(["Captured decision at 75.5 s","Value"],[
        ["driver_state / status / alert_level",f"{selected['driver_state']} / {selected['status']} / {selected['alert_level']}"],
        ["Raw score / smoothed score",f"{selected['score']:.3f} / {selected['smoothed_score']:.3f}"],
        ["Reason",selected["reason"]],
    ],[width*.56,width*.44]))
    cap("The prolonged-closure override can select DROWSY below the normal score threshold. The v2 packet has 14 fields; the exact legacy adapter is allowed only for usable observations. SG6 still needs to accept the richer fault policy.")

    # 8. Compact verification, rubric and next actions.
    heading(story,8,"Verification and evaluation checklist")
    suites=[c for c in verification["checks"] if c.get("test_count")]
    cards([(str(suites[0]["test_count"]),"SG5 / handoff tests"),(str(suites[1]["test_count"]),"SG1 / SG4 tests"),(str(suites[2]["test_count"]),"SG2 tests")])
    left=[picture("robust_c_confusion.png",w=(width-13)/2,max_height=155),p("Robust C row percentages; UNKNOWN remains an error, not an excluded sample.","small")]
    right=[p("255 recorded passes","h2"),p("Timing, gaps, sessions, missing cues, strict metrics and the real SG6 validator are tested.","small"),p("SG2 tests use a separate Torch environment; connected EAR inference needs no Torch.","small"),p("Implementation PR 21 merged. Source pins and recorded runs are preserved.","small")]
    pair(left,right)
    story.append(Spacer(1,8))
    story.append(table(["Stage 1 criterion","Evidence / remaining action"],[
        ["A 15  |  7 + 4 + 2 + 2","Working demos; primary/backup; contracts and runbook; measured tests and limitations"],
        ["B 10  |  3 + 3 + 2 + 2","Shared repo; owned tasks/board; README/evidence; preserved coordination records"],
        ["C 5  |  2 + 1 + 2","SG6 must verify actual Jetson boot, stack and camera; PC execution is not target proof"],
    ],[width*.34,width*.66]))
    story.append(p("Demonstration order","h2"))
    story.append(code('$py = ".\\.venv\\Scripts\\python.exe"\n& $py -m module_5.midterm.demo --scenario drowsy\n& $py -m module_5.midterm.pipeline `\n  --video module_1/data/videos/driver_sample_01.mp4 --show\n& $py -m module_5.midterm.evaluate --plot\n& $py -m unittest discover -s module_5/midterm/tests -v'))
    cap("Use the prepared .venv interpreter from the repository root; complete commands are in scripts.md. SG6's check_platform.py requires an explicit --camera test on the physical device.")
    story.append(p("<b>Open:</b> SG3 threshold/geometry review, SG4 availability/gap acceptance, SG6 v2/fault policy, independent real-stream labels and target profiling. Tracked separately in issue 20.","small"))
    story.append(p("Sources and reproducibility","h2"))
    story.append(p("Course sources: Midterm Evaluation pp. 1-2; Semester Guide pp. 3-7; Week 5 Tasks pp. 1-3, 6; Allocation p. 2 rows 48-49. Primary runtime: Google MediaPipe Face Landmarker documentation. Full source revisions: integration/sg5_midterm_sources.json. Visual assets and pinned data: report/assets/evidence_bundle.json and evidence_manifest.json.","small"))
    story.append(p("Repository: <link href='https://github.com/Sananismm/CV_Drowsinees_Detection' color='#245D83'>Sananismm/CV_Drowsinees_Detection</link> &nbsp; | &nbsp; <link href='https://github.com/Sananismm/CV_Drowsinees_Detection/pull/21' color='#245D83'>implementation PR 21</link> &nbsp; | &nbsp; <link href='https://github.com/users/Sananismm/projects/2' color='#245D83'>team board (private)</link>","small"))

    for name, drawing in (("evidence_sources.svg",evidence_map(layout)),("connected_pipeline.svg",layout["pipeline_diagram"]()),("decision_quality_flow.svg",layout["decision_diagram"]())):
        renderSVG.drawToFile(drawing,str(assets/name))
    manifest={"source_commit":bundle["source_commit"],"text_hash_policy":"Normalize CRLF to LF for .json, .jsonl, .txt and .svg; binary files use exact bytes","files":{item.name:asset_hash(item) for item in sorted(assets.iterdir()) if item.is_file() and item.name!="evidence_manifest.json"}}
    (assets/"evidence_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return story
