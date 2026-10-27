"""Eye crops synchronized by source frame identity and SG-1 image dimensions.

OpenCV image operations: https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html
Crop margins are SG-2 engineering parameters, not medically validated settings.
"""
import math
import numpy as np
from .adapters import eye_packet, finite, integer


def extract_eye_crops(frame, record, *, frame_id, timestamp_sec, tolerance_sec=0.002):
    if not integer(frame_id) or not finite(timestamp_sec) or timestamp_sec < 0:
        raise ValueError("invalid synchronized frame identity/time")
    packet = eye_packet(record)
    if frame_id != packet["frame_id"] or abs(timestamp_sec-packet["timestamp_sec"]) > tolerance_sec:
        raise ValueError("video frame/SG-1 identity or timestamp mismatch")
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("expected HxWx3 BGR frame")
    if frame.shape[:2] != (packet["image_height"], packet["image_width"]):
        raise ValueError("video frame/SG-1 dimensions mismatch")
    if not packet["eyes_valid"]:
        return [], []
    crops, boxes = [], []
    for side in ("left", "right"):
        p = np.asarray(packet[side+"_eye_points_xy_normalized"])*[frame.shape[1],frame.shape[0]]
        eye_width = float(np.linalg.norm(p[0]-p[3]))
        if eye_width < 4:
            return [], []
        # Fixed aspect/size relative to corners avoids a vanishing crop on closure.
        cx,cy = (p[0]+p[3])/2
        half_w,half_h = eye_width*0.8,eye_width*0.55
        x1,y1,x2,y2 = math.floor(cx-half_w),math.floor(cy-half_h),math.ceil(cx+half_w),math.ceil(cy+half_h)
        # Reject clipped crops rather than silently changing their field of view.
        if x1 < 0 or y1 < 0 or x2 > frame.shape[1] or y2 > frame.shape[0]:
            return [], []
        crops.append(frame[y1:y2,x1:x2].copy())
        boxes.append([x1,y1,x2,y2])
    return crops,boxes
