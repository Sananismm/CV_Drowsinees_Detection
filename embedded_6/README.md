# SG6 - Embedded Deployment and System Integration

**CS-477 Computer Vision | SEECS CV Face-Off 2026**

**Members:** Muhammad Sanan Khan and Muhammad Sami

**Target:** NVIDIA Jetson Orin Nano 8 GB

Start with the [post-midterm submission](midterm/README.md). It contains executable
entry points, setup commands, algorithm choices, historical detector measurements,
fresh PC verification, source attribution, and the remaining submission checklist.

YuNet is the primary SG6 detector candidate; Haar is the backup. Neither supplies
the detailed eye landmarks needed by SG2. The optional integrated demo uses SG1's
MediaPipe landmark detector and pinned SG2/SG4/SG5 code with an SG3-derived adapter.

The code previously available only on `sg6` is restored in this submission branch.
Historical October documentation under [docs/](docs/README.md) retains its original
context; use the new midterm package for current checkout availability and commands.

## AI and source disclosure

OpenAI Codex assisted with this November submission: repository inspection,
restoring existing SG6 source, camera portability and measurement metadata,
benchmark/verification utilities, tests, and documentation. The members must review
the results. Earlier code retains its subgroup provenance; historical AI use is
not independently known. See [SOURCE_ATTRIBUTION.md](midterm/SOURCE_ATTRIBUTION.md)
for source links, pinned revisions, and model hashes.
