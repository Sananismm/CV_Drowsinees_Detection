# SG-1 Live Demonstration in VS Code

This demo runs the existing SG-1 face/landmark detector and opens a separate preview window. It has two explicit input choices: a live webcam or a downloaded video. Choose the one you want to show; the code does not silently change sources. The demo is an SG-1 geometry demonstration, not a drowsiness decision.

## Open and present

1. Open `module_1/SG1-Live-Demo.code-workspace` in VS Code. If asked, trust the workspace so the Python debugger can run.
2. Open **Run and Debug** with `Ctrl+Shift+D`.
3. Select **SG-1: Live webcam** or **SG-1: Downloaded video fallback** from the drop-down.
4. Press `F5` (or `Ctrl+F5` to run without debugging). The webcam choice uses camera index `0`; the fallback opens `Downloads/P10427801_na.mp4`.
5. The preview is a separate OpenCV window. Click that window, then press `Q` or `Esc` to stop. The demo does not record or upload video.

On this machine the project-local `.venv` and verified model are set up. Camera 0 opened and processed a short test without saving footage; the brief 60-frame visible-preview check returned `NO_FACE` throughout, so check your camera view and lighting with your face visible before presenting. A saved-video preview also completed on 500 frames. These checks are not an accuracy evaluation.

## Double-click alternatives

Without using Run and Debug, double-click `scripts/start_live_camera.cmd` for camera 0, or `scripts/start_saved_video.cmd` for the downloaded sample. The launchers use the project-local Python environment and keep the terminal open on an error. The video launcher checks for the sample in your Windows Downloads folder.

## Run from the VS Code terminal

From `module_1/`:

```powershell
.\.venv\Scripts\python.exe scripts\live_demo.py --camera 0
```

To show an approved saved video instead:

```powershell
.\.venv\Scripts\python.exe scripts\live_demo.py --video "$env:USERPROFILE\Downloads\P10427801_na.mp4"
```

The preview uses the `lower_resolution` configuration by default: 192 px long side and 0.50 detection/presence/tracking thresholds. It shows face status, landmark count, the landmark-derived box and mesh. To preview the 256 px backup instead, add `--preset baseline` to a terminal command or the launch configuration's arguments. On-screen FPS is an interactive display rate and is not the full-video benchmark; use `MIDTERM_REAL_VIDEO_RESULTS.md` for the documented comparison.

## Setup on another computer

Install Python 3.12 and the VS Code Python extension, then run from `module_1/`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\download_model.py
.\.venv\Scripts\python.exe scripts\verify_setup.py --smoke-model
```

The model and environment are local and excluded from Git. Place an approved video at the path used by the fallback launch configuration, or edit that configuration's `--video` argument.

## If the webcam does not open

- Allow camera access for desktop apps in Windows privacy settings, and close other programs using the camera.
- Try another camera index by changing `--camera 0` to `--camera 1` in the VS Code launch configuration or terminal command.
- Select the downloaded-video fallback explicitly if camera hardware is unavailable. It demonstrates SG-1 running on saved input, as permitted by the midterm instructions.

Confirm permission to present any identifiable driver footage before sharing it.
