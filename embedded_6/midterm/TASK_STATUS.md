# SG6 ownership, status and blockers

**Members:** Muhammad Sanan Khan and Muhammad Sami. Sanan's repository account is
`Sananismm`; Sami's GitHub account has not been supplied. The owners below are a
proposed division for the members to review, not evidence of prior assignments.

| Existing issue | Proposed accountable owner | Evidence-based status | Blocker / next acceptance |
| --- | --- | --- | --- |
| [#35 Jetson setup](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/35) | Muhammad Sanan Khan | Historical setup documented; fresh target verification pending | Capture current boot, OS, runtime, camera and power-mode metadata |
| [#36 Haar/YuNet](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/36) | Muhammad Sanan Khan | Implemented; historical benchmark recorded; PC regression checked | Review package and reproduce on target with private frames |
| [#37 Live camera](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/37) | Muhammad Sami | Pending physical validation | Live camera, GUI, read failure and processing FPS on target |
| [#38 SG1-SG5 integration](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/38) | Muhammad Sanan Khan; Muhammad Sami supports target testing | Synthetic interoperability checked; live deployment pending | MediaPipe model/environment, target run, SG3/SG4/SG6 acceptance in #20 |
| [#40 GPIO/buzzer](https://github.com/Sananismm/CV_Drowsinees_Detection/issues/40) | Muhammad Sami | Pending hardware implementation/validation | Agree wiring and sensor-fault policy; execute physical acceptance |
| Submission evidence (this package) | Both members | Prepared for review | Original README confirmation; video; board update; email |

## Board update checklist

Existing team board: [Computer-Vision Driver Drowsiness Monitoring](https://github.com/users/Sananismm/projects/2).
The GitHub connector does not expose project-board editing. Windows browser
automation stopped because the current Edge URL could not be determined reliably;
no live board status update is claimed. Existing issues #35-#38 and #40 were open
and unassigned at inspection on 17 November 2026.

For each listed card, set the agreed member's assignee, current status and blocker
using the table above. Use In review for #36 only after linking this submission;
keep physical camera/integration/GPIO tasks pending or in progress until target
evidence exists. Do not close #20 on the strength of synthetic tests. Sami's
account must be confirmed before assigning a GitHub username.

## Final submission checks

- [x] SG6 member names and target recorded.
- [x] Primary YuNet / backup Haar and selection reasons documented.
- [x] Previously missing executable SG6 code restored with attribution.
- [x] Run commands, dependency pins, historical latency and AI disclosure supplied.
- [ ] Members review the reconstructed evaluation README against the presented version.
- [ ] Members confirm task ownership and update the live project board.
- [ ] Recover the original evaluation demo, or ask the instructor whether a clearly
  labelled replacement recording is acceptable.
- [ ] Add the permitted video link and attach the video to the subgroup email.
- [ ] Review and send the email; record actual send evidence only after sending.
