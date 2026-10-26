
"""
SG-2: Eye State and Closure Analysis
Driver Drowsiness Detection Project

Purpose:
    Receives facial landmark information, calculates Eye Aspect Ratio (EAR),
    classifies the eye state, and detects continuous eye-closure events.

Week 5 preliminary EAR threshold: 0.15
"""

import numpy as np


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

EAR_THRESHOLD = 0.15

# MediaPipe landmark indices used for EAR calculation
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


# ---------------------------------------------------------
# DISTANCE FUNCTION
# ---------------------------------------------------------

def euclidean_distance(point1, point2):
    """
    Calculate Euclidean distance between two 2-D points.
    """

    return np.linalg.norm(
        np.array(point1) - np.array(point2)
    )


# ---------------------------------------------------------
# EAR CALCULATION
# ---------------------------------------------------------

def calculate_ear(landmarks, eye_indices, image_width, image_height):
    """
    Calculate Eye Aspect Ratio (EAR) for one eye.

    EAR =
    (vertical distance 1 + vertical distance 2)
    ------------------------------------------------
              2 * horizontal distance
    """

    points = []

    for index in eye_indices:

        landmark = landmarks[index]

        x = landmark.x * image_width
        y = landmark.y * image_height

        points.append((x, y))

    p1, p2, p3, p4, p5, p6 = points

    vertical_1 = euclidean_distance(p2, p6)
    vertical_2 = euclidean_distance(p3, p5)

    horizontal = euclidean_distance(p1, p4)

    # Prevent division by zero
    if horizontal == 0:
        return None

    ear = (
        vertical_1 + vertical_2
    ) / (2.0 * horizontal)

    return ear


# ---------------------------------------------------------
# BOTH-EYE EAR
# ---------------------------------------------------------

def calculate_average_ear(
    landmarks,
    image_width,
    image_height
):
    """
    Calculate EAR for left and right eyes
    and return their average.
    """

    left_ear = calculate_ear(
        landmarks,
        LEFT_EYE,
        image_width,
        image_height
    )

    right_ear = calculate_ear(
        landmarks,
        RIGHT_EYE,
        image_width,
        image_height
    )

    if left_ear is None or right_ear is None:
        return None, None, None

    average_ear = (left_ear + right_ear) / 2.0

    return left_ear, right_ear, average_ear


# ---------------------------------------------------------
# EYE-STATE CLASSIFICATION
# ---------------------------------------------------------

def classify_eye_state(
    average_ear,
    threshold=EAR_THRESHOLD
):
    """
    Classify eye state using EAR.

    EAR < threshold  -> CLOSED
    EAR >= threshold -> OPEN

    If EAR is unavailable -> UNKNOWN
    """

    if average_ear is None or np.isnan(average_ear):
        return "UNKNOWN"

    if average_ear < threshold:
        return "CLOSED"

    return "OPEN"


# ---------------------------------------------------------
# SG-2 OUTPUT PACKET
# ---------------------------------------------------------

def create_output_packet(
    frame_id,
    timestamp_sec,
    average_ear,
    valid=True,
    closure_event=None,
    threshold=EAR_THRESHOLD
):
    """
    Create standardized SG-2 output for SG-4.
    """

    if not valid or average_ear is None:
        eye_state = "UNKNOWN"
        ear_value = None

    else:
        eye_state = classify_eye_state(
            average_ear,
            threshold
        )

        ear_value = round(float(average_ear), 4)

    output = {
        "frame_id": int(frame_id),
        "timestamp_sec": round(float(timestamp_sec), 3),
        "eye_state": eye_state,
        "ear": ear_value,
        "ear_threshold": threshold,
        "valid": bool(valid),
        "closure_event": closure_event
    }

    return output
