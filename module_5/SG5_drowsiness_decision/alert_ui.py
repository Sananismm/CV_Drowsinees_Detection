# =============================================================================
# SG5 - Alert output (kept SEPARATE from the decision logic, as the PDF asks)
# =============================================================================
# The decision methods live in sg5_three_methods.py. That file saves its
# decisions to results/<drive>_predictions.csv. This file only READS those
# decisions and shows/beeps the alerts. It contains no decision logic.
#
# RUN FROM TERMINAL (VS Code PowerShell) - run sg5_three_methods.py first, then:
#
#   cd "C:\Users\Hp Probook\Desktop\SG5_drowsiness_decision\SG5_drowsiness_decision"
#   & "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" alert_ui.py
#
# Options (add after alert_ui.py):
#   --method A | B | C          which method's decisions to alert on (default C)
#   --drive drive1_synthetic    which drive (default drive1_synthetic)
#   --speed 10                  replay 10x faster than real time (0 = instant, default)
#   --no-beep                   print only, no sound
# Example:
#   & "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" alert_ui.py --method A --speed 10
#
# ALERT RULES
#   WARNING  -> print a yellow-style message + one short beep
#   DROWSY   -> print a loud message + three long beeps
#   Only when the state goes UP, so the driver is not beeped every 0.1 s.
#   Going back down is printed quietly.
# =============================================================================
import argparse
import csv
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LEVEL = {"NORMAL": 0, "WARNING": 1, "DROWSY": 2}


def beep(state, sound_on):
    if not sound_on:
        return
    try:
        import winsound                           # Windows only
        if state == "WARNING":
            winsound.Beep(800, 200)
        else:
            for _ in range(3):
                winsound.Beep(1500, 400)
    except (ImportError, RuntimeError):
        print("\a", end="", flush=True)           # fallback: terminal bell


def show_alert(t, old, new, sound_on):
    if LEVEL[new] > LEVEL[old]:
        if new == "WARNING":
            print(f"[{t:7.1f} s]  (!)  WARNING  - showing signs of tiredness")
        else:
            print(f"[{t:7.1f} s]  (!!!) DROWSY  - WAKE UP!")
        beep(new, sound_on)
    else:
        print(f"[{t:7.1f} s]       back to {new}")


def main():
    ap = argparse.ArgumentParser(description="SG5 alert output")
    ap.add_argument("--method", choices=["A", "B", "C"], default="C")
    ap.add_argument("--drive", default="drive1_synthetic")
    ap.add_argument("--speed", type=float, default=0.0)
    ap.add_argument("--no-beep", action="store_true")
    a = ap.parse_args()

    path = os.path.join(HERE, "results", f"{a.drive}_predictions.csv")
    if not os.path.exists(path):
        sys.exit(f"Not found: {path}\nRun sg5_three_methods.py first.")

    print(f"Alerts for method {a.method} on {a.drive}\n" + "-" * 55)
    state, prev_t, n_alerts = "NORMAL", None, 0
    with open(path) as f:
        for row in csv.DictReader(f):
            t, new = float(row["time_s"]), row[a.method]
            if a.speed > 0 and prev_t is not None:
                time.sleep((t - prev_t) / a.speed)
            prev_t = t
            if new != state:
                show_alert(t, state, new, not a.no_beep)
                n_alerts += LEVEL[new] > LEVEL[state]
                state = new
    print("-" * 55 + f"\n{n_alerts} alerts raised (warnings + drowsy)")


if __name__ == "__main__":
    main()
