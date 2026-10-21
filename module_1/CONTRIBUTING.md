# Contributing to SG-1

## Branches

- Use `sg1/week<number>-<short-task>`.
- Start from the latest reviewed SG-1 branch.
- Merge current `main` before requesting final review.
- Do not force-push a shared branch without agreement.

## Commits

- Keep one technical purpose per commit.
- Use clear messages.
- Record who performed experiments.
- Do not use documentation-only commits to imply code contribution.

Examples:

```text
feat(sg1): add versioned output schema
test(sg1): add no-face contract fixture
docs(sg1): document SG2 eye-landmark handoff
fix(sg1): reject incomplete landmark arrays
```

## Pull requests

A pull request must include:

- problem statement;
- changed behavior;
- test commands;
- test results;
- interface impact;
- known limitations;
- sample output when the schema changes.

At least one other team member should review it.
Interface changes require SG-2, SG-3 and SG-6 review.

## Code rules

- Keep frame ID and timestamp through every stage.
- Do not invent confidence values.
- Handle `NO_FACE` explicitly.
- Keep raw videos and model binaries out of Git.
- Add a test for each bug fix.
- Keep generated outputs outside source folders.

## Documentation rules

- Use short sentences.
- State facts and limits separately.
- Mark proposals as proposals.
- Record decisions in `docs/DECISION_LOG.md`.
- Update `docs/STATUS.md` when a task changes state.
- Update `CHANGELOG.md` for user-visible changes.

## Before review

- Run static compilation.
- Run unit tests.
- Run interface tests.
- Run one saved-video smoke test.
- Check Git status.
- Check that no private footage or model binary is staged.
