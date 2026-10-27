# SG-1 Midterm: Downloaded-Video Rerun

Run date: 2026-10-27. This is a fresh run of the current `sg1` code on the five downloaded clips used in the Week 5 comparison. It is separate from both the older Week 5 timing run and the generated contact-sheet fallback.

## Input and procedure

Each configuration processed every frame of the same five 1920x1080, 25 FPS MP4 files: 600, 720, 577, 560 and 475 frames respectively, for **2,932 frames** per configuration. File names, frame counts and SHA-256 hashes are in [`input_manifest.csv`](../results/midterm_real_20261027/input_manifest.csv). The videos are not included in the repository; source and redistribution permissions should be confirmed before wider sharing.

The runs used Python 3.12.10, MediaPipe 0.10.35, OpenCV 4.11.0 and NumPy 1.26.4 on a Windows desktop. The model bundle SHA-256 was `64184E229B263107BC2B804C6625DB1341FF2BB731874B0BCC2FE6544E0BC9FF`. Configurations ran sequentially with stride 1, no frame limit and **without video rendering** for the benchmark. Each per-clip output passed `verify_experiment.py`; the aggregate script checked complete frame IDs and matched labels.

## Full-video comparison

| Configuration | Frames with a returned face/landmarks | Coverage | Mean processing-path latency | p95 latency | Combined desktop throughput |
|---|---:|---:|---:|---:|---:|
| Baseline: 256 px / 0.50 | 2,931 / 2,932 | 99.966% | 7.963 ms | 8.512 ms | 77.251 FPS |
| Lower threshold: 256 px / 0.35 | 2,931 / 2,932 | 99.966% | 7.956 ms | 8.483 ms | 78.274 FPS |
| Lower resolution: 192 px / 0.50 | 2,931 / 2,932 | 99.966% | 6.189 ms | 6.681 ms | 90.791 FPS |

These are one desktop run; performance varies by machine and load. Processing-path latency includes external resizing, color conversion and the MediaPipe video call, but not all decoding/serialization. Combined throughput is total processed frames divided by the sum of each clip's recorded wall seconds; this runner includes detector initialization/teardown, video decoding, per-frame validation and output writing. It is not camera-to-alert system FPS. It cannot be directly compared with older runs that used different timing boundaries or with the separate video-rendered demo runs.

The 192 px setting was about **17.5% faster** end-to-end than the 256 px baseline in this run, with the same observed face-return coverage. The 0.35 experiment changes face-detection, face-presence and tracking thresholds together; the result does not isolate any one threshold. A returned face is not proof that the driver, rather than another visible person, was selected, or that landmark locations are correct.

## Provisional box agreement and failure review

The 20 reference boxes were estimated visually by an AI assistant, and independent human review is not recorded. All 20 contain a face; there are no labeled no-face negatives and no landmark-point labels. At IoU >= 0.50, all three configurations had 17 matches and three below-threshold box overlaps. The resulting box precision/recall/F1 are each **0.85 against those provisional references**, not independently validated detector accuracy. A below-threshold overlap contributes one false positive and one false negative in the evaluator; reference boxes must be reviewed before these are characterized as model failures.

The three reference-box disagreement frames are 432 and 576 of `P1043061_na` and frame 224 of `P1043080_na`. Their per-configuration IoUs are in [`mismatch_cases.csv`](../results/midterm_real_20261027/mismatch_cases.csv). The only `NO_FACE` output over all 2,932 frames was the entirely black frame 576 of `P1043079_na`; an actual sanitized output is in [`example_no_face.json`](../results/midterm_real_20261027/example_no_face.json).

Tracked tables: [`aggregate_comparison.csv`](../results/midterm_real_20261027/aggregate_comparison.csv), [`per_clip_comparison.csv`](../results/midterm_real_20261027/per_clip_comparison.csv), and [`provisional_box_metrics_summary.csv`](../results/midterm_real_20261027/provisional_box_metrics_summary.csv). The aggregation tool computes pooled p95 from individual frame times and pooled counts rather than averaging per-clip p95 values.

## Reproduce the full comparison

After the one-time setup in [`QUICKSTART.md`](QUICKSTART.md), run from `module_1/` in PowerShell. This takes longer than the short demo and creates full per-frame outputs locally. Choose a new result directory; the per-video runner overwrites files in an existing output directory.

```powershell
$python = '.\.venv\Scripts\python.exe'
$downloads = Join-Path $env:USERPROFILE 'Downloads'
$runRoot = 'results\my_full_midterm_run'
if (Test-Path $runRoot) { throw 'Choose a new result directory to avoid overwriting.' }
$clips = @('P10427801_na', 'P1043061_na', 'P1043079_na', 'P1043080_na', 'P1043128_na')
foreach ($clip in $clips) {
    $inputPath = Join-Path $downloads ($clip + '.mp4')
    $outputPath = Join-Path $runRoot ('benchmarks\' + $clip)
    & $python scripts\run_experiment.py --input $inputPath --output-dir $outputPath
    if ($LASTEXITCODE -ne 0) { throw "Experiment failed: $clip" }
    & $python scripts\verify_experiment.py $outputPath
    if ($LASTEXITCODE -ne 0) { throw "Verification failed: $clip" }
}
& $python scripts\summarize_video_runs.py `
    --runs-dir (Join-Path $runRoot 'benchmarks') `
    --labels-dir 'results\downloaded_samples\ground_truth' `
    --output-dir (Join-Path $runRoot 'summaries') `
    --require-complete
if ($LASTEXITCODE -ne 0) { throw 'Aggregation failed' }
```

The summarizer requires matching configurations, model hash, complete frame IDs and a reference-label file for every clip. It refuses to overwrite an existing summary directory. Compare input hashes to `input_manifest.csv` before treating a rerun as the same data.

## Annotated demonstrations

Separately from the full-video benchmark, the first 100 frames of each of the five original clips were processed with `--save-video` for all three settings: **15 annotated demo videos**. Each demo output passed the experiment verifier. The videos, per-frame landmark streams and raw source footage remain local. Because drawing/encoding adds overhead, those short video runs are not the performance table above. The first 100 demo frames do not cover all selected reference-box frame IDs, so do not score these short demos against the full 20-frame label set.

See [`MIDTERM_DEMO.md`](MIDTERM_DEMO.md) for commands and presentation order, and [`MIDTERM_METHOD_DECISION.md`](MIDTERM_METHOD_DECISION.md) for the primary/backup rationale. Have a person review the reference boxes and test additional poses, occlusions, lighting and no-face cases before making an accuracy claim.
