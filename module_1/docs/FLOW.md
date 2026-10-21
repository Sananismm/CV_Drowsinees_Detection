# SG-1 Execution and Data Flow

## System position

```text
Camera or saved video
        |
        v
SG-1 Face and Landmarks
        |
        +------> SG-2 Eye and Blink Analysis
        |
        +------> SG-3 Yawn and Facial Cues
                       |
                       v
              SG-4 Temporal Analysis
                       |
                       v
              SG-5 Drowsiness Decision
                       |
                       v
              SG-6 Deployment and Alert
```

SG-1 does not decide drowsiness.
SG-1 supplies face geometry.

## Setup flow

```text
Create virtual environment
        |
        v
Install requirements
        |
        v
Download model
        |
        v
Verify model hash
        |
        v
Select approved video
        |
        v
Run experiment or live pipeline
```

## One-frame runtime flow

```text
1. OpenCV reads a BGR frame.
2. The frame ID is stored.
3. The timestamp is calculated.
4. The long side is reduced to 256 or 192 pixels.
5. The aspect ratio is preserved.
6. BGR is converted to RGB.
7. The frame is wrapped as a MediaPipe image.
8. MediaPipe runs face landmark detection.
9. The code checks for a face mesh.
10. The code creates one output record.
```

## Successful face path

```text
Face mesh returned
        |
        v
Read x and y for each landmark
        |
        v
Keep normalized landmark coordinates
        |
        v
Find minimum and maximum x and y
        |
        v
Map the box to original-frame pixels
        |
        v
Clamp the box to the image boundary
        |
        v
Return status OK
```

## No-face path

```text
No face mesh returned
        |
        v
status = NO_FACE
face_bbox_xyxy = null
landmarks_xy_normalized = []
landmark_count = 0
detection_confidence = null
```

Downstream modules must treat this record as invalid.
It must not become eye closure or yawning evidence.

## Experiment flow

```text
Load experiment.json
        |
        v
Open the same input video
        |
        v
Run baseline
        |
        v
Run lower threshold
        |
        v
Run lower resolution
        |
        v
Write one result set per configuration
        |
        v
Compare coverage and speed
        |
        v
Evaluate boxes on the same labeled frames
        |
        v
Review failures
        |
        v
Select a provisional configuration
```

## Saved output flow

```text
SG-1 output dictionary
        |
        +------> JSONL prediction record
        |
        +------> failure CSV when NO_FACE
        |
        +------> annotated video when enabled
        |
        +------> aggregate comparison row
```

## Integration flow

```text
SG-1 output
        |
        v
Validate schema version and status
        |
        v
Check landmark count and required indices
        |
        +------> SG-2 selects eye landmarks and calculates EAR
        |
        +------> SG-3 selects mouth landmarks and calculates MAR
```

SG-2 and SG-3 must not run a second face detector in the final pipeline.
They must consume the same SG-1 result for the same frame.

## Failure flow

| Failure | Required action |
|---|---|
| Video cannot open | Stop with a clear error |
| Model is missing | Stop and tell the user to run the download script |
| No face | Emit a valid `NO_FACE` record |
| Landmark list is incomplete | Mark the record invalid before SG-2 or SG-3 |
| Timestamp is not increasing | Correct or reject it before MediaPipe VIDEO mode |
| Output video cannot open | Stop and report the output path |
| Dependency import fails | Stop and report the missing package |
