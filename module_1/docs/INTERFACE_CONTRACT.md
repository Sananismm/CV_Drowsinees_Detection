# SG-1 V1 Interface Contract

## Status

Status: **IMPLEMENTED DRAFT - downstream acceptance required**

Required reviewers:

- SG-1
- SG-2
- SG-3
- SG-6

Do not call this contract frozen until the reviewers accept it in writing.

## Producer and consumers

Producer: SG-1 Face and Landmark Detection.

Direct consumers:

- SG-2 Eye/Blink Analysis.
- SG-3 Yawn/Facial Cues.

SG-6 uses the contract for integration.

## Transport

- In-process: Python dictionary.
- Saved experiments: one JSON object per JSONL line.
- Encoding: UTF-8.
- One record represents one processed frame.

## Proposed record

The following abbreviated illustration shows two landmarks instead of the full 478 while retaining the production count. It is **not** a complete valid `OK` record and must not be passed to the validator. For a valid complete 478-point record, use [`sg1_v1_ok.json`](../../interfaces/examples/sg1_v1_ok.json); the corresponding valid missing-face example is [`sg1_v1_no_face.json`](../../interfaces/examples/sg1_v1_no_face.json).

```json
{
  "schema_version": "sg1.v1",
  "frame_id": 0,
  "timestamp_ms": 0,
  "image_width": 1280,
  "image_height": 720,
  "status": "OK",
  "face_bbox_xyxy": [410, 88, 832, 612],
  "landmarks_xy_normalized": [[0.42, 0.25], [0.43, 0.24]],
  "landmark_count": 478,
  "landmark_topology": "mediapipe_face_landmarker_478",
  "detection_confidence": null,
  "config_name": "lower_resolution",
  "inference_ms": 6.27
}
```

The detector emits all listed fields.
The runtime validator rejects missing, unknown or invalid fields.
The machine-readable schema is `interfaces/sg1_v1.schema.json`.
Tracked positive and no-face fixtures are under `interfaces/examples/`.

## Field rules

| Field | Type | Unit | Rule |
|---|---|---|---|
| `schema_version` | string | none | Must equal `sg1.v1` |
| `frame_id` | integer | frame | Non-negative source-frame index |
| `timestamp_ms` | integer | millisecond | Must increase during one VIDEO-mode stream |
| `image_width` | integer | pixel | Original frame width |
| `image_height` | integer | pixel | Original frame height |
| `status` | string | none | `OK` or `NO_FACE` |
| `face_bbox_xyxy` | array or null | pixel | `[x1,y1,x2,y2]` in original-frame coordinates |
| `landmarks_xy_normalized` | array | fraction | `[x,y]` relative to full frame |
| `landmark_count` | integer | point | Must equal the landmark array length |
| `landmark_topology` | string | none | Defines landmark ordering |
| `detection_confidence` | number or null | 0 to 1 | Null when the API exposes no observed score |
| `config_name` | string | none | Configuration used for this record |
| `inference_ms` | number | millisecond | SG-1 processing duration |

## Bounding-box convention

- Order: left, top, right, bottom.
- Coordinate system: original frame pixels.
- Origin: top-left.
- Right and bottom describe the maximum extent.
- Coordinates are clamped to the image bounds.
- The box is derived from landmarks.
- It is not an independent detector box.

## Landmark convention

- Order follows the frozen MediaPipe topology.
- Each item is `[x,y]`.
- Values are normalized by frame width and height.
- Values near image boundaries can be outside `[0,1]`.
- Consumers must validate all required indices.
- Consumers must not assume a topology from count alone.

## Valid face rule

```text
face_valid =
    status == "OK"
    and face_bbox_xyxy is not null
    and landmark_count == len(landmarks_xy_normalized)
    and every required consumer index exists
```

Do not use the configured threshold as observed confidence.

## No-face record

```json
{
  "schema_version": "sg1.v1",
  "frame_id": 576,
  "timestamp_ms": 23040,
  "image_width": 1920,
  "image_height": 1080,
  "status": "NO_FACE",
  "face_bbox_xyxy": null,
  "landmarks_xy_normalized": [],
  "landmark_count": 0,
  "landmark_topology": "mediapipe_face_landmarker_478",
  "detection_confidence": null,
  "config_name": "baseline",
  "inference_ms": 6.85
}
```

## Consumer rules

SG-2:

- Review the proposed eye indices in `scripts/sg1_contract.py`.
- Do not treat those indices as frozen until SG-2 accepts them.
- Convert normalized points only when pixel coordinates are required.
- Return `UNKNOWN` when `face_valid` is false.
- Do not rerun face detection in the integrated pipeline.

SG-3:

- Read the agreed mouth indices.
- Return invalid or unknown cues when `face_valid` is false.
- Do not treat missing landmarks as a yawn.
- Do not rerun face detection in the integrated pipeline.

SG-4:

- Use a validity flag.
- Do not require a fabricated numeric face confidence.

SG-6:

- Validate `schema_version`.
- Reject incompatible records with a clear error.

## Contract tests

Implemented locally:

- Valid `OK` and `NO_FACE` records.
- Draft 2020-12 schema validity.
- Fixtures accepted by the machine schema.
- Missing and unknown fields rejected.
- Wrong schema version and topology rejected.
- Truncated landmarks rejected.
- Non-finite landmarks rejected.
- Out-of-bounds boxes rejected.
- SG-2 valid and invalid adapters.
- SG-3 explicit-index adapter behavior.
- Monotonic detector timestamps.

Still requires downstream execution:

- SG-2 consumes both adapter fixtures.
- SG-3 confirms mouth indices and consumes both SG-1 fixtures.
- SG-6 loads and rejects records by version as agreed.

## Change control

Any field removal or meaning change creates a new schema version.
New optional fields can remain within V1 after team review.
Record every accepted change in `DECISION_LOG.md`.
