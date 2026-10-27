# SG5 — Drowsiness Decision & Alert Logic (Driver Drowsiness Stream, Week 5)

**Pipeline:** Camera → SG1 Face/Landmarks → SG2 Eye state / SG3 Yawn → SG4 Temporal analysis → **SG5 Decision** → Alert

SG5 takes the temporal indicators from SG4 and decides the driver's state: **NORMAL → WARNING → DROWSY**.

## Files
| File | What it is |
|---|---|
| `sg5_three_methods.py` | **Main file.** The 3 decision methods, comparison with ground truth, graphs |
| `alert_ui.py` | Alert output (print + beep), **kept separate from the decision logic** |
| `make_synthetic_data.py` | Creates the 2 synthetic test drives (already created, only needed to regenerate) |
| `data/drive1_synthetic.csv` | Test drive 1 (5 min) with ground truth |
| `data/drive2_synthetic.csv` | Test drive 2 (4 min) with ground truth |
| `results/` | Graphs and CSVs produced by the main file |

## How to run (PowerShell, VS Code terminal)
```powershell
cd "C:\Users\Hp Probook\Desktop\7th sem\cv\project\SG5_drowsiness_decision\SG5_drowsiness_decision"
& "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" -m pip install numpy matplotlib
& "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" sg5_three_methods.py
```
The `pip` line is only needed once. Add `--no-show` to save the graphs without opening windows.

Then, to see the alerts a driver would get (beeps on Windows):
```powershell
& "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" alert_ui.py --method C --speed 10
```
Use `--method A`, `B` or `C`, `--drive drive2_synthetic` for the other drive, `--speed 0` for instant, and `--no-beep` for silent.

## Input and output (interface)
**Input:** CSV, one row every 0.1 s, as SG4 would send it.

| Column | Meaning |
|---|---|
| `time_s` | time in seconds |
| `face_valid` | 1 = face found, 0 = face lost |
| `perclos` | fraction of time eyes were closed in the last 30 s (0–1) |
| `eye_closure_s` | how long the eyes have been closed right now (s) |
| `long_blinks` | blinks ≥ 0.5 s in the last 30 s |
| `yawn_count` | yawns in the last 60 s |
| `gt_state` | ground truth (test data only, not used by the methods) |

**Output:** for every row, each method gives `state` = `NORMAL`, `WARNING` or `DROWSY`. These are saved in `results/<drive>_predictions.csv`.

## The synthetic data: how it is formed
We do not yet have real SG4 output, so the test data is simulated (see `make_synthetic_data.py`):
1. A hidden **drowsiness level d(t)** from 0 (alert) to 1 (very drowsy) is scripted over time.
2. **Eyes are simulated at 30 fps.** Higher d gives more blinks, longer blinks and more long blinks. Micro-sleeps (eyes shut 1.5–3 s) happen when d > 0.7, and one is placed on purpose in Drive 1.
3. **Yawns are simulated**, more often when drowsy. **Talking creates false yawn detections.**
4. **Detector errors are added:** random wrong eye readings (more under glare) and moments when the face is lost.
5. These are converted into **SG4-style indicators** (PERCLOS, closure length, long blinks, yawn count) at 10 rows/s.
6. **Ground truth** comes from d(t): NORMAL if d < 0.4, WARNING if 0.4–0.7, DROWSY if ≥ 0.7. Each micro-sleep is DROWSY from its start until 3 s after.

| Drive | Story |
|---|---|
| Drive 1 (300 s) | Alert → micro-sleep at 75 s → gets drowsy from 100 s → very drowsy 160–210 s → recovers |
| Drive 2 (240 s) | Talking with false yawns (0–80 s) → tired but not drowsy (85–160 s) → glare and frequent face loss (165–240 s) |

## The three methods
**Method A: Threshold rules (baseline).** Each row is checked on its own with simple if-rules:
- DROWSY if PERCLOS ≥ 0.22 or eyes closed ≥ 1.5 s.
- WARNING if PERCLOS ≥ 0.10, or 2+ yawns, or 3+ long blinks.
- Otherwise NORMAL.

It is simple, fast and easy to explain. It has no memory, so it can jump between states quickly (flicker), and any single cue (like yawns from talking) can trigger a warning.

**Method B: Weighted score.** All cues are combined into one score from 0 to 1:
`score = 0.45·PERCLOS + 0.20·eye closure + 0.20·long blinks + 0.15·yawns` (each cue first scaled to 0–1).
- DROWSY if score ≥ 0.50.
- WARNING if score ≥ 0.20.

One noisy cue alone has less effect, so it is fooled less by talking. It still has no memory, and a single short micro-sleep may not raise the score enough.

**Method C: State machine.** It uses the same score as B, plus these memory rules:
- **Smoothing:** the score is averaged over about 2 s, so single-frame noise is ignored.
- **Hysteresis:** the threshold to go up (e.g. 0.65 for DROWSY) is higher than the threshold to come down (0.53). This stops flicker around one threshold.
- **Confirm before going up:** the score must stay high for 1 s.
- **Hold before going down:** the method stays in a state for at least 3 s.
- **Micro-sleep override:** eyes closed ≥ 1.5 s means DROWSY immediately.

It is the most stable (fewest state changes) and reacts fast to micro-sleeps. The cost is that it is slower to come back down, and it has more parameters to tune.

All methods output NORMAL during the first 5 s (SG4 windows are still filling) and keep their last state when the face is lost. All parameters are at the top of `sg5_three_methods.py`.

## Alert output (separate from decision logic)
The manual asks to keep decision logic separate from the alert UI. `sg5_three_methods.py` only **decides** and saves the decisions to `results/<drive>_predictions.csv`. `alert_ui.py` only **reads** those decisions and alerts:
- **WARNING:** message plus one short beep.
- **DROWSY:** message plus three long beeps.
- Alerts fire only when the state goes **up**, so the driver is not beeped every 0.1 s.

On the Jetson, the beep can later be replaced by a buzzer or screen without touching the decision code.

## How the methods are compared with ground truth
| Metric | Meaning |
|---|---|
| Accuracy | % of rows where the method's state equals the ground truth |
| DROWSY caught | real DROWSY events where the method said DROWSY (during it or up to 5 s after) |
| False alerts | DROWSY periods by the method when the driver was not drowsy |
| Delay | seconds from start of the real DROWSY event to the method's DROWSY |
| State changes | how often the output changes (flicker; fewer is calmer for the driver) |

**Graphs produced in `results/`:**
- `drive1_synthetic_methods_vs_ground_truth.png` and `drive2_...`: input, ground truth, and each method over time. Red shading marks wrong rows.
- `overall_comparison.png`: bar chart of all metrics for A, B, C.
- `confusion_matrices.png`: for each true state, what each method said.

## Real data that can be used instead (online)
These public datasets contain **videos**, not SG4 indicators. To use them for SG5, the videos must first go through our SG1→SG4 pipeline; SG5 then runs on SG4's output.

| Dataset | What it has | Use for SG5 | Access |
|---|---|---|---|
| **NTHU-DDD** (National Tsing Hua University Drowsy Driver Detection, ACCV 2016 workshop) | 36 subjects in a driving simulator, IR video, glasses/night/sunglasses scenarios; frame-level labels for drowsiness, eyes, head and mouth | Best fit: frame-level drowsiness labels can serve as ground truth | By request from NTHU Computer Vision Lab; download link Not Verified |
| **UTA-RLDD** (UT Arlington Real-Life Drowsiness Dataset) | About 30 h of RGB video, 60 people, real (not acted) drowsiness; one video each for alert, low vigilance, drowsy | Testing with real drowsiness; labels are per video, not per frame | Search "UTA-RLDD"; official download page Not Verified |
| **YawDD** (Yawning Detection Dataset) | In-car videos of drivers silent, talking/singing, and yawning | Testing whether talking causes false yawn alerts | IEEE DataPort, open access with a free IEEE account: https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset |

## Reference implementations (bonus: feasibility screening)
Candidates were found by web search and **cloned and inspected on 7 Oct 2026**. Scores use the PDF's 100-point weights. These are our scores from reading the code; the manual asks the subgroup to re-score itself, so check and adjust before submitting. Anything we could not confirm is marked **Not Verified** and scored 0.

### Candidate details
| Item | 1. e-candeloro / Driver-State-Detection | 2. hazeeq911 / Driver-Drowsiness-Detection | 3. akshaybahadur21 / Drowsiness_Detection | 4. neelanjan00 / Driver-Drowsiness-Detection |
|---|---|---|---|---|
| Link | github.com/e-candeloro/Driver-State-Detection | github.com/hazeeq911/Driver-Drowsiness-Detection | github.com/akshaybahadur21/Drowsiness_Detection | github.com/neelanjan00/Driver-Drowsiness-Detection |
| What it does | Webcam → MediaPipe landmarks → EAR, gaze, head pose, rolling PERCLOS → "tired", "asleep", "looking away", "distracted" | YOLOv5 detects open/closed eyes per frame | dlib landmarks → EAR; alert if EAR < 0.25 for 20 consecutive frames | dlib landmarks → EAR, mouth ratio (yawn), head tilt; on-screen messages |
| Decision logic like SG5? | **Yes**: time-based timers with decay, PERCLOS over 60 s (threshold 0.2), closure ≥ 2 s = asleep | **No**: only per-frame eye classification (closer to SG2) | Simple: consecutive-frame counter | Simple: separate per-frame thresholds |
| Language / framework | Python 3.12, OpenCV, MediaPipe | Python 3.8, PyTorch, YOLOv5 | Python, OpenCV, dlib, imutils, scipy | Python, OpenCV 4.2, dlib 19.20 (pinned) |
| Jetson / edge evidence | Not Verified (none found) | README gives Jetson Nano setup steps; not reproduced by us | Not Verified | Not Verified |
| Reported accuracy | None reported | Notebook: mAP@0.5 ≈ 0.99 for eye open/closed on 49 validation images (tiny, self-collected) | None reported | None reported |
| Reported FPS / latency | Not Verified (has a show-FPS option) | Not Verified | Not Verified | Not Verified |
| Pretrained model | MediaPipe model via download script | `driver updated.pt` included | dlib 68-landmark model included | dlib model included |
| Dataset | None (live webcam) | Small self-collected set included as zip | None | None |
| License | MIT | No license file found | MIT | No license file found |
| Last commit | Aug 2026, has unit tests | Sep 2022 | Jun 2025 | Jul 2022 |
| Cloned? | Yes | Yes | Yes | Yes |
| Executed? | **Partly**: decision class run on a scripted eye-closure input; flagged "asleep" ~2 s after closure, as documented. Full camera app not run. | No | No (needs webcam + dlib) | No (needs webcam + dlib) |
| Major risk | MediaPipe on Jetson (ARM) + Python 3.12 requirement Not Verified | Not SG5 logic; old PyTorch 1.7 build steps | Eye-only, frame-count based (FPS-dependent) | Old pinned versions; no license |

### Weighted feasibility scores (/100)
| Criterion (weight) | 1. e-candeloro | 2. hazeeq911 | 3. akshaybahadur21 | 4. neelanjan00 |
|---|---|---|---|---|
| End-to-end working (15) | 15 | 5 | 12 | 13 |
| Python / source code (15) | 15 | 13 | 14 | 13 |
| Jetson / edge evidence (15) | 0 | 12 | 0 | 0 |
| Accuracy evidence (10) | 0 | 5 | 0 | 0 |
| Reproducibility / docs (10) | 9 | 5 | 6 | 5 |
| Pretrained weights (10) | 9 | 10 | 10 | 9 |
| Real-time feasibility on Orin Nano (10) | 7 | 6 | 6 | 6 |
| Dataset availability (5) | 0 | 2 | 0 | 0 |
| SG5 interface compatibility (5) | 4 | 0 | 2 | 3 |
| Repository maturity / license (5) | 5 | 1 | 3 | 1 |
| **Total** | **64** | **59** | **53** | **50** |

### Decision
- **Primary reference: e-candeloro / Driver-State-Detection (64).** It is the only candidate with real time-based decision logic (PERCLOS, closure timers with decay, unknown-face handling), similar to our Method C. It is MIT-licensed, recently maintained and has tests. **Risk:** MediaPipe and Python 3.12 on Jetson are unverified, so SG6 should check this.
- **Backup: akshaybahadur21 / Drowsiness_Detection (53).** It is a simple, MIT-licensed EAR + consecutive-frame rule, the same idea as our Method A.
- **Not used for SG5: hazeeq911 (59).** It scores high only because of its Jetson Nano and model evidence, but it has no drowsiness decision logic, so it cannot serve the SG5 interface. Pass it to SG2/SG6 as an eye-state and Jetson reference.
- **Rejected: neelanjan00 (50).** It has no license, old pinned dependencies, and only per-frame messages without a combined decision.

### Still to do by the team (for execution-evidence credit)
1. Clone the primary on your own laptop: `git clone https://github.com/e-candeloro/Driver-State-Detection.git`
2. Run it on a webcam and note the FPS shown.
3. Ask SG6 to try installing MediaPipe on the Jetson Orin Nano.
4. Replace any "Not Verified" cell you can confirm, and re-score.

## Limitations
- The results come from **synthetic data with only 2 drives**. They show how the methods behave, not real-world accuracy; this must be re-checked on real SG4 output.
- All methods react slowly to gradual drowsiness and recover slowly, because SG4's PERCLOS uses a 30 s window and yawns a 60 s window.
- When the face is lost, the last state is kept. A head dropping forward (falling asleep) is not yet detected.
