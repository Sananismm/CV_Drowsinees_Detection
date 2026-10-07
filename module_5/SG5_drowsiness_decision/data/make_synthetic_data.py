r"""
Creates the two synthetic test drives in data/ (already included, you only need
this if you want to regenerate or change them).

Run (PowerShell):
  & "$env:USERPROFILE\anaconda3\envs\ganenv\python.exe" make_synthetic_data.py

HOW THE DATA IS FORMED
1. A hidden "drowsiness level" d(t) from 0 (alert) to 1 (very drowsy) is
   scripted over time, e.g. alert -> slowly getting drowsy -> recovers.
2. Eyes are simulated at 30 frames/s. The higher d is, the more often the
   driver blinks, the longer each blink lasts, and the more "long blinks"
   (>= 0.5 s) happen. Micro-sleeps (eyes shut 1.5-3 s) occur when d > 0.7,
   and one is also inserted on purpose in Drive 1.
3. Yawns are simulated (more frequent when drowsy). Talking produces FALSE
   yawn detections, to test whether a method is fooled by them.
4. Real detectors make mistakes, so noise is added: random wrong eye
   readings (more under "glare") and moments where the face is lost.
5. These frame-level cues are turned into what SG4 would send us, 10 times
   per second: PERCLOS (fraction of eye-closed time in last 30 s), current
   eye-closure length, long blinks in last 30 s, yawns in last 60 s.
6. Ground truth (gt_state) comes from d(t): NORMAL if d < 0.4,
   WARNING if 0.4 <= d < 0.7, DROWSY if d >= 0.7. Every micro-sleep is
   labelled DROWSY from its start until 3 s after it ends.
"""
import csv
import os

import numpy as np

FPS = 30            # simulated camera frame rate
OUT_EVERY = 3       # write one row every 3 frames = 10 rows per second


def make_drive(duration, d_points, seed, microsleeps=(), talking=(), glare=()):
    """d_points: [(time, d), ...] drowsiness profile. talking/glare: [(start, end), ...]"""
    rng = np.random.default_rng(seed)
    n = int(duration * FPS)
    t = np.arange(n) / FPS
    d = np.interp(t, *zip(*d_points))
    in_any = lambda ranges: np.array([any(a <= x < b for a, b in ranges) for x in t])
    is_talking, is_glare = in_any(talking), in_any(glare)

    # --- step 2: true eye closures -----------------------------------------
    closed = np.zeros(n, bool)
    sleeps = list(microsleeps)
    for t0, dur in microsleeps:
        closed[int(t0 * FPS):int((t0 + dur) * FPS)] = True
    i = 0
    while i < n:
        if closed[i]:
            i += 1
            continue
        u = rng.random()
        p_sleep = max(0, d[i] - 0.7) / 0.3 * 0.6 / 60 / FPS     # micro-sleep chance
        p_blink = (14 + 10 * d[i]) / 60 / FPS                   # blink chance
        if u < p_sleep:
            dur = rng.uniform(1.5, 3.0)
            sleeps.append((t[i], dur))
        elif u < p_sleep + p_blink:
            if rng.random() < 0.03 + 0.45 * d[i]:
                dur = rng.uniform(0.5, 0.6 + 1.4 * d[i])        # long blink
            else:
                dur = max(0.08, rng.normal(0.15 + 0.25 * d[i], 0.04))
        else:
            i += 1
            continue
        k = int(round(dur * FPS))
        closed[i:i + k] = True
        i += k + 6                                              # eyes open briefly after

    # --- step 4: detector noise and face loss -------------------------------
    noise = np.where(is_glare, 0.08, 0.02)
    seen_closed = closed ^ (rng.random(n) < noise)
    seen_closed = np.convolve(seen_closed, [1, 1, 1], "same") >= 2   # SG4 smoothing
    face_ok = np.ones(n, bool)
    i = 0
    while i < n:
        if rng.random() < (1 / 12 if is_glare[i] else 1 / 90) / FPS:
            k = int(rng.uniform(0.5, 3.0) * FPS)
            face_ok[i:i + k] = False
            i += k
        i += 1
    seen_closed &= face_ok

    # --- step 3: yawns -------------------------------------------------------
    yawn = np.zeros(n, bool)
    i = 0
    while i < n:
        p_true = (0.3 + 2.5 * d[i]) / 60 / FPS
        p_false = (4.0 if is_talking[i] else 0.3) / 60 / FPS
        u = rng.random()
        if u < p_true:
            k = int(rng.uniform(4, 6) * FPS)
        elif u < p_true + p_false:
            k = int(rng.uniform(1, 3.5) * FPS)                  # talking mistaken for yawn
        else:
            i += 1
            continue
        yawn[i:i + k] = True
        i += k
    yawn &= face_ok

    # --- step 5: SG4-style indicators ---------------------------------------
    def events(mask):  # list of (start_time, end_time)
        m = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
        return [(s / FPS, e / FPS) for s, e in zip(np.where(m == 1)[0], np.where(m == -1)[0])]
    blinks = events(seen_closed)
    yawns = [e for e in events(yawn) if e[1] - e[0] >= 2.5]     # yawn must last >= 2.5 s

    # --- step 6: ground truth -------------------------------------------------
    gt = np.where(d >= 0.7, 2, np.where(d >= 0.4, 1, 0))
    for t0, dur in sleeps:
        gt[int(t0 * FPS):int((t0 + dur + 3) * FPS)] = 2

    rows, run = [], 0.0
    for k in range(n):
        run = run + 1 / FPS if seen_closed[k] else 0.0
        if k % OUT_EVERY:
            continue
        lo = max(0, k - 30 * FPS)
        valid = face_ok[lo:k + 1].sum()
        rows.append({
            "time_s": round(t[k], 2),
            "face_valid": int(face_ok[k]),
            "perclos": round(seen_closed[lo:k + 1].sum() / valid, 3) if valid else 0.0,
            "eye_closure_s": round(run, 2),
            "long_blinks": sum(1 for s, e in blinks if t[k] - 30 < e <= t[k] and e - s >= 0.5),
            "yawn_count": sum(1 for s, e in yawns if t[k] - 60 < e <= t[k]),
            "gt_state": ("NORMAL", "WARNING", "DROWSY")[gt[k]],
        })
    return rows


def save(rows, name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"saved {path} ({len(rows)} rows)")


if __name__ == "__main__":
    # Drive 1 (5 min): alert -> micro-sleep at 75 s -> gradually drowsy -> very drowsy -> recovers
    save(make_drive(300, [(0, .1), (100, .1), (160, 1), (210, 1), (215, .1), (300, .1)],
                    seed=1, microsleeps=[(75, 2.2)]), "drive1_synthetic.csv")
    # Drive 2 (4 min): talking (false yawns) -> tired but not drowsy -> glare + face lost often
    save(make_drive(240, [(0, .1), (80, .1), (85, .55), (160, .55), (165, .1), (240, .1)],
                    seed=2, talking=[(0, 80)], glare=[(165, 240)]), "drive2_synthetic.csv")
