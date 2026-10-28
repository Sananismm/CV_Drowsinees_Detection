# SG6 Viva Preparation

> **Repository availability:** This report describes a Jetson worktree snapshot. The revised demo, its tests, and `embedded_6/integrated/` were local and uncommitted at the time of publication and are not present on `main`; commands that use those files require that local snapshot. Do not assume a fresh `main` checkout can run them.

**Why Jetson?** The project targets an embedded ARM64 device with local camera access and sufficient resources for a measured CPU baseline. We used the available Orin Nano; we have not established a comparative platform study.

**Why edge inference?** It permits local processing without requiring a network service and supports a low-latency design. Actual latency depends on capture, inference, display and other modules.

**Why YuNet over Haar?** On the same 150 private frames, YuNet averaged 24.23 ms versus Haar 40.32 ms and supplies five keypoints. This result does not prove superior accuracy or robustness.

**Latency versus FPS?** Latency is time per call in milliseconds; inference FPS here is number of calls divided by summed call times. Demo processing FPS also includes capture and loop work. Neither is a full system performance claim unless all stages are measured.

**Why is 100% face coverage not 100% accuracy?** It means each unlabelled test frame had at least one detection. It does not establish whether a box was correct, whether multiple faces were missed, or the false-positive rate.

**Why two OpenCV environments?** System OpenCV 4.5.4 is preserved; the YuNet demo uses the isolated 4.14.0 environment. System Python's Haar test failed because cv2.data was absent. The experimental integrated snapshot uses a separate pinned MediaPipe/OpenCV environment.

**Why cannot YuNet provide EAR?** Five coarse facial keypoints do not provide the six contour points per eye used by SG2. The optional SG1 Face Landmarker supplies denser geometry.

**How are SG1–SG5 integrated?** In the separate experimental snapshot, SG1 records go through SG2 eyes and an SG3-derived mouth adapter, then a bridge to the real SG4 temporal engine and SG5 decision engine. The primary detector demo does not run that chain. Synthetic tests check selected handoffs; owner approval and live validation remain.

**Which tests use camera data?** The 150-image detector benchmark uses private recorded camera frames. A historical Haar live-camera JSON reports 150 frames and 18.04 FPS but lacks key run metadata. No successful live run of the revised demo was captured in this assistant session. A README describes a 120-frame integrated video run without the original log in the reviewed evidence.

**Which tests are synthetic?** The current integrated unit tests use generated landmarks and controlled mouth/eye states; the older SG2→SG4 and SG5 tests use supplied numerical values. Mock-camera demo tests are not hardware tests.

**How is the project tested?** Unit tests cover loading, missing model, zero faces, measurements and cleanup; recorded frames exercise real detector inference; synthetic interface tests exercise data flow. Real-camera, long-duration and labelled robustness checks remain.

**How are invalid frames handled?** The demo reports a read failure, returns an error and releases capture. SG1 validates identity and geometry; downstream unknown or stale evidence must be distinguished from a normal driver state. Those behaviours are separately tested, not a safety guarantee.

**Why no CUDA claim?** OpenCV reported zero CUDA-enabled devices in the earlier audit and the benchmark requested no CUDA. CPU is the measured baseline; hardware capability alone is not evidence of use.

**What did SG6 contribute?** Camera acquisition, platform/environment setup, detector comparison, timing/metrics, integration wiring/tests, documentation and private evidence handling. Algorithms copied from other teams and upstream models remain attributed to their owners.

**What remains?** Verify the current demo on the connected camera, GUI and failure paths; obtain subgroup agreement, validate real landmarks and temporal decisions, test physical alerts and measure robustness and resource use. Synthetic outputs do not establish safe driver monitoring.

**Final evaluation plan?** Complete real-camera and long-duration testing, representative labelled data and lighting/pose studies; validate timing, missing data, subgroup handoffs and physical alerts with owners. Do not claim unmeasured performance.
