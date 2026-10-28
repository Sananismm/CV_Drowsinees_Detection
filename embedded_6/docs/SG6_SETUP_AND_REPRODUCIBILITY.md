# SG6 Setup and Reproducibility

Commands run on the Jetson host from `~/CV_Drowsinees_Detection`. Do not overwrite functioning system Python, CUDA or JetPack. The existing demo environment is `~/sg6-yunet-env`; no complete pinned manifest for it was found, so recreating it byte-for-byte from the repository is not established. Check its interpreter and installed versions before use.

## Prerequisites and checks

```bash
cd ~/CV_Drowsinees_Detection
cat /etc/nv_tegra_release
uname -m
ls -l /dev/video*
id
~/sg6-yunet-env/bin/python -c 'import sys,cv2,numpy; print(sys.version); print(cv2.__version__, numpy.__version__); print("CUDA devices:", cv2.cuda.getCudaEnabledDeviceCount())'
ls -l embedded_6/models/face_detection_yunet_2023mar.onnx
~/sg6-yunet-env/bin/python embedded_6/Integration/run_midterm_demo.py --help
```

Device permissions depend on the host's video group and desktop ACL; inspect `ls -l` and `id` before requesting appropriate access from the administrator. Do not assume access from a container or sandbox. Camera indices can include metadata-only nodes. GUI requires a working display and Python Tkinter; headless does not. YuNet uses OpenCV 4.14.0 in the existing isolated environment. System OpenCV 4.5.4 lacks cv2.data here; use the isolated interpreter. Do not assume an OpenCV build supports CUDA merely because Jetson has a GPU.

## Existing environment and execution

```bash
source ~/sg6-yunet-env/bin/activate
python embedded_6/Integration/run_midterm_demo.py --detector yunet --headless --duration 60 --save-metrics
python embedded_6/Integration/run_midterm_demo.py --detector haar --headless --duration 60 --save-metrics
python -m unittest discover -s embedded_6/Integration -p test_midterm_demo.py -v
python embedded_6/Integration/benchmark_detectors.py
```

Benchmark requires exactly 150 private `embedded_6/evidence/benchmark_frames/frame_*.jpg` files. It overwrites the ignored detector_benchmark.json; preserve a copy before rerunning if the old result is needed. Inputs, configuration, warm-up and timing boundaries are described in the [report](SG6_MIDTERM_TECHNICAL_REPORT.md). Repeating after a reboot or load change will give different timings. The script does not save per-frame latency or labelled accuracy.

## Separate integrated environment

The repository documents this provisioning command for a **new** environment; it requires network and compatible ARM64 wheels, so avoid recreating an existing working environment without first preserving it:

```bash
python3 -m venv --system-site-packages embedded_6/.venv-integrated
embedded_6/.venv-integrated/bin/python -m pip install -r embedded_6/integrated/requirements.txt
embedded_6/.venv-integrated/bin/python -m unittest discover -s embedded_6/integrated/tests -v
```

The pinned MediaPipe model is `embedded_6/models/face_landmarker.task`; the integrated README provides its official download URL and SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. The model and venv are ignored. This is separate from the tracked YuNet ONNX model. The integrated launcher refuses a hash mismatch. The optional video command requires an actual local video path and valid reported FPS; see integrated/README.md. No example path is presented as a real input here.

## Evidence and troubleshooting

The main demo saves no frames; optional JSON includes detector, configuration, dimensions, counts, mean/median latency, processing FPS and failure counts. Driver drops are unknown. Treat an exit status of 1 and zero processed frames as a failure. Protect private evidence; the repository's embedded_6/.gitignore excludes evidence/ but check `git status --ignored` before sharing. If the camera fails, inspect host nodes, permissions, selected index and competing processes; if display fails, use --headless. System Python errors should be resolved by invoking the isolated interpreter, not a system-wide upgrade. Historical OS and benchmark data are dated and should not be assumed current.
