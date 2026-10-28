# SG6 midterm readiness

Audit date: 2026-10-28. The current checkout is `sg6-week5-integration` at `b4bf9ec`; initial worktree was clean. Remote mirror obtained separately: `main` a5570c4, `sg1` 5fcb936, `sg2` 0bc84fc, `sg2-midterm-integration` ca73a39, `sg3` e3661b7, `sg4` 059705b, `saman` 1019abe, `sg5` 9e0de17, `sg5-midterm-integration` bf15c3b, SG6 b4bf9ec. Local origin refs are stale; the protected checkout `.git` rejected fetch. No merge was performed. These hashes are a snapshot, not a guarantee of current remote state.

## Rubric evidence

**Algorithm and demonstration (15 marks):** Haar and YuNet exist, and the 150-frame private benchmark reran. Coverage was 100% for both; Haar 40.74 ms / 24.55 inference FPS, YuNet 25.02 ms / 39.96 inference FPS. This is inference-only, not accuracy or end-to-end throughput. New YuNet demo and unit tests exist; live camera and GUI remain unverified. Existing SG2→SG4 and SG5 tests run actual older subgroup logic with synthetic inputs, not a live system.

**GitHub and collaboration (10 marks):** SG6 has commits and documented attributed reference copies. GitHub issue #20 requests SG6 handoff and hardware acceptance. Newer work exists on `saman`, `sg2-midterm-integration`, and `sg5-midterm-integration`; GitHub board and PR completeness were not independently established. No marks claimed.

**Hardware and environment (5 marks):** ARM64 Tegra, Jetson Linux R36.4.7, Python 3.10.12, isolated OpenCV 4.14.0 / NumPy 2.2.6 and system OpenCV 4.5.4 / NumPy 1.21.5 observed. YuNet loaded and processed a synthetic blank frame. The assistant environment could not see a video device. The user subsequently ran a headless live capture successfully: five 640×480 frames, one face reported on frames 1 and 5. GUI operation with the camera remains to be confirmed after switching display to Tkinter. MediaPipe is absent in system Python; ARM64 installation and compatibility have not been established.

## Subgroup integration and ownership

SG1 `sg1` source uses MediaPipe Tasks FaceLandmarker, normalized landmark arrays, millisecond timestamps and nullable detection confidence. SG2 old EAR expects landmark objects; the newer SG2 adapter consumes SG1 arrays, checks topology and dimensions, and converts milliseconds to seconds. It needs target execution and interface acceptance. YuNet supplies five points and cannot supply SG2's six points per eye.

SG3's old source evaluates simulated MAR; newer Week 8 source contains Colab-specific commands and a video/MediaPipe implementation. Live Jetson integration and its output agreement with SG4 are unverified. SG4's old notebook outputs PERCLOS as 0–100 and does not supply all legacy SG5 inputs; the newer `saman` SG4 source explicitly emits fractional PERCLOS and fields including closure duration and event counts. SG5's old logic expects fractional PERCLOS and six named inputs. Newer SG5 work includes an SG6 handoff; inspect and agree its stale/insufficient evidence policy before use. Do not infer unavailable measurements or equate missing face with normal.

The reference SG2, SG4 and SG5 files match the locally cached old `origin/sg2`, `origin/sg4`, and `origin/sg5` sources byte-for-byte, but do not represent all newer integration branches. Mock schemas are SG6 fixtures, not proof of agreed contracts. Timestamp, confidence, missing face, yawn semantics, and event-window alignment still need cross-owner verification. Algorithms belong to their respective subgroups.

## Readiness decision

**Not yet examiner-ready for a live demonstration:** connect a camera, run the guide, validate GUI/headless and face/no-face behavior, and record actual throughput. Full SG1–SG5, alert hardware, remote board and new integration branches remain unverified. See MIDTERM_TASKS.md and MIDTERM_DEMO_GUIDE.md.
