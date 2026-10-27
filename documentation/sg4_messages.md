# Draft messages from SG-4

## To SG-2 (eye) and SG-3 (yawn / head pose)

> Hi SG-2 and SG-3, SG-4 here. We take your per-frame output and turn it into PERCLOS, microsleeps, yawn and nod events for SG-5.
>
> **SG-2:** thanks for the draft. We already read it as-is: `frame_id`, `timestamp` (s), `eye_state`, `eye_valid` and `ear`. Two asks:
> 1. Can you send an `eye_closure_prob` (0 open, 1 closed), even uncalibrated? If not, tell us the EAR or CNN threshold behind CLOSED.
> 2. Can you add a per-frame eye `confidence` (0–1)?
>
> **SG-3:** please confirm or change these per-frame fields: `yawn_prob` (0–1), `mar`, `pitch_deg`, `yaw_deg`, `roll_deg`, `confidence` (0–1). Also confirm the sign convention: **pitch negative = head down**.
>
> Timestamps should be SG-1's capture clock (ms or s are both fine). Use null for missing values; we never treat null as closed.
>
> Schema: `interfaces/sg4_input_v1.schema.json`. Only our `adapters.py` changes if you rename things.

## To SG-5 (FYI, no questions)

> Hi SG-5, SG-4 here. FYI: our output now matches your request table exactly (v1.1, 10 Hz, flat JSON).
>
> | Field | Meaning |
> |---|---|
> | `time_s` | capture time in s |
> | `perclos` | 0–1, 60 s window |
> | `face_valid` | 0/1, current frame |
> | `long_blinks` | closures ≥ 0.5 s in the last 30 s |
> | `yawn_count` | yawn events in the last 60 s |
> | `eye_closure_s` | live closure; 0.0 when face lost |
> | `nod_count` | optional extra |
>
> - **Golden outputs to test against now:** `interfaces/mocks/sg5_expected/*.jsonl` (alert, drowsy, yawns_nods, face_lost, noisy).
> - **Check any file:** `python module_4/tools/check_sg5_compat.py <file.jsonl>`. It prints PASS/FAIL per field.
> - **Full contract:** `interfaces/sg4_output_v1_1.schema.json` and `documentation/interface_tracking.md`.
>
> Tell us only if something should change. Windows are one config line on our side.
