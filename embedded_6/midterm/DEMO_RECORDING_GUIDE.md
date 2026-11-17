# SG6 demo recording guide

The original evaluation video is currently unavailable. This guide helps create a
new recording if a replacement is accepted; it is not evidence that one exists.

Aim for a short, clear 2-3 minute recording on the actual target:

1. Show a title with SG6, Muhammad Sanan Khan, Muhammad Sami, the actual recording
   date and source commit. State whether this is the evaluation or a replacement.
2. Show the Jetson and USB camera, then current OS/Python/OpenCV metadata. Do not
   describe a PC-only run as target deployment.
3. From the repository root run the YuNet demo with `--frames 150 --save-metrics`.
   Show face boxes and the overlay, then no-face behavior. State this is face
   detection, not a complete drowsiness decision.
4. Run Haar with the same frame limit. Show the saved frame counts, resolution,
   mean/median detector latency and processing FPS. The two live runs are not a
   paired benchmark because they observe different frames.
5. If private paired frames are available, run the benchmark command in
   [RUN_COMMANDS.md](RUN_COMMANDS.md). Show its timing boundary and results.
6. Show the synthetic integration and handoff verification results, explicitly
   identifying them as synthetic software evidence. Show the live integrated
   pipeline only if actually executed; do not substitute synthetic output.
7. Demonstrate clean shutdown; state what remains pending, including hardware
   alerts if they have not been tested.

Record with an existing screen recorder or a phone filming the target display.
Keep camera imagery private until all visible people consent. Retain the original
video locally, supply a reviewer-accessible link, and attach it to the email.
Record source commit and actual metrics with the footage so results are traceable.
