# Face Detection Model

Model: face_detection_yunet_2023mar.onnx
Architecture: YuNet
Source: OpenCV Zoo

Upstream repository:
https://github.com/opencv/opencv_zoo

Model location:
models/face_detection_yunet/

The model is used by SG6 to evaluate face detection
performance on the NVIDIA Jetson Orin Nano.

Consult the upstream model and repository license files
for applicable redistribution and attribution conditions.

YuNet provides face bounding boxes and five facial keypoints.
It does not provide the detailed eye landmarks required for
SG2's Eye Aspect Ratio (EAR) computation.
