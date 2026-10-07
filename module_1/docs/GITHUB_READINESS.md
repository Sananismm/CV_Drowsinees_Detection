# SG-1 GitHub readiness checklist

Use these steps in the team's shared repository; do not create a separate project repository unless the team lead asks.

1. Put this folder under the shared project's `module_sg1/` (or the team's agreed SG-1 folder).
2. Work on a feature branch such as `sg1/w5-detector-config-study`.
3. Keep model weights and raw driver videos out of Git. Commit code, configuration, README, and anonymized result tables only where allowed.
4. Commit incremental changes with descriptive messages, for example:
   - `Add MediaPipe SG1 video inference interface`
   - `Add controlled threshold and resolution comparison`
   - `Document labeled box evaluation and failure review`
5. Ask for review before merging into the stable integration branch.
6. Link the task/issue to the branch or pull request and attach the experiment CSV and analysis after running it.

## Suggested board cards

- `W5 | SG1 | Run baseline and alternatives on common driver clips` - labels `W5`, `SG1`, `Test`; evidence: comparison CSV and metadata.
- `W5 | SG1 | Label representative face boxes` - labels `W5`, `SG1`, `Data`; evidence: reviewed CSV with near/far, pose and occlusion examples.
- `W5 | SG1 | Review detector failures and choose Week 6 setting` - labels `W5`, `SG1`, `Analysis`; evidence: completed experiment record and chosen config.
- `W5 | SG1 | Verify interface with SG2 and SG3` - labels `W5`, `SG1`, `Integration`; evidence: agreed sample JSON and interface test by downstream groups.

This local package provides the code and documentation for those tasks. Remote repository access, branch creation and board updates must be done in the team's GitHub repository by a member with access.
