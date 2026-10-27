# Shared Interface Artifacts

This directory contains versioned, machine-readable contracts shared between sub-groups.

## SG-1 V1

Status: **implemented by SG-1; not frozen until SG-2, SG-3 and SG-6 accept it**.

| Artifact | Purpose |
|---|---|
| [`sg1_v1.schema.json`](sg1_v1.schema.json) | Draft 2020-12 JSON Schema for one SG-1 frame record |
| [`examples/sg1_v1_ok.json`](examples/sg1_v1_ok.json) | Real positive output with 478 landmarks |
| [`examples/sg1_v1_no_face.json`](examples/sg1_v1_no_face.json) | Standard no-face output |
| [`examples/sg1_to_sg2_v1_ok.json`](examples/sg1_to_sg2_v1_ok.json) | Proposed SG-2 adapter packet for a valid face |
| [`examples/sg1_to_sg2_v1_no_face.json`](examples/sg1_to_sg2_v1_no_face.json) | Proposed SG-2 invalid-face packet |
| [`examples/sg1_v1_invalid_missing_schema.json`](examples/sg1_v1_invalid_missing_schema.json) | Negative fixture that consumers must reject |
| [`SG1_TO_SG2_AI_HANDOFF.md`](SG1_TO_SG2_AI_HANDOFF.md) | Machine-oriented SG-2 connection instructions and tests |
| [`SG1_TO_SG3_AI_HANDOFF.md`](SG1_TO_SG3_AI_HANDOFF.md) | Machine-oriented SG-3 connection instructions and tests |

The normative human-readable rules are in
[`module_1/docs/INTERFACE_CONTRACT.md`](../module_1/docs/INTERFACE_CONTRACT.md).

Run the contract tests from the repository root:

```powershell
module_1\.venv\Scripts\python.exe -m unittest module_1.tests.test_contract -v
```

Validate a JSON or JSONL file with the runtime validator:

```powershell
module_1\.venv\Scripts\python.exe module_1\scripts\validate_output.py interfaces\examples\sg1_v1_ok.json
```

## Change control

- Do not edit V1 field meanings without SG-1, SG-2, SG-3 and SG-6 review.
- Additive fields still require schema, fixture and consumer-test updates.
- Breaking changes require a new schema version.
- Record accepted decisions in [`module_1/docs/DECISION_LOG.md`](../module_1/docs/DECISION_LOG.md).
