# SG6 latency and FPS evidence

## Historical Jetson comparisons

These are transcribed from the repository's existing benchmark notes and October
technical report, not newly measured in November. The private frames and raw
measurement JSON are unavailable in this checkout, so the figures cannot be
independently reproduced here. Each row is a distinct run; do not combine them.

| Recorded run | Haar mean / detector FPS | YuNet mean / detector FPS | Source |
| --- | --- | --- | --- |
| Original run; date unspecified | 31.65 ms / 31.59 | 17.89 ms / 55.91 | [BENCHMARK_RESULTS.md](../BENCHMARK_RESULTS.md), original table |
| 28 Oct 2026, first rerun | 40.74 ms / 24.55 | 25.02 ms / 39.96 | Same file, Re-run section |
| 28 Oct 2026, additional rerun | 40.32 ms / 24.80 | 24.23 ms / 41.27 | Same file, Additional rerun; [technical report](../docs/SG6_MIDTERM_TECHNICAL_REPORT.md), section 8 |

All comparisons report 150 private 640x480 frames and 150/150 frames with a
detection per detector. The additional rerun uses five warm-ups, OpenCV 4.14.0
default CPU, and reported Jetson Linux R36.4.7. The original environment note
reports R36.4.3; retain that distinction. Mean timings are rounded; saved FPS may
differ slightly from `1000 / rounded mean`.

The latest historical run supports the selected YuNet candidate. It measures the
detector call including grayscale conversion for Haar and input-size setup for
YuNet. Capture, decoding, display and downstream inference are excluded.
Coverage is not precision, recall or labelled accuracy. Thermal/power settings,
subject count, lighting and independent ground truth were not recorded.

## Historical live-camera observation

The October technical report separately describes an older Haar-only camera run:
150 processed frames, 135 with a detection, 46.95 ms mean detector time and
18.04 processing FPS. Its raw JSON is absent here and lacked timestamp, actual
resolution and runtime configuration in the report. It is not evidence of live
operation of the newly restored revision and is not directly comparable to the
paired detector benchmark.

## Fresh verification and new target measurement

[verification.json](evidence/verification.json) records camera-free software checks
on this PC. Test-suite duration is not algorithm latency. No new Jetson latency,
complete-pipeline FPS, GPU utilization, power or memory result is claimed.

Use [RUN_COMMANDS.md](RUN_COMMANDS.md) for the new paired benchmark and live demo.
The utilities save actual metadata and per-frame detector timings, enabling a
future target result to be reviewed without overwriting historical measurements.
Share this page and the reviewed run JSON through the repository with the other
subgroups; a meeting or independent owner sign-off is not implied by that link.
