"""Small independent eye-image CNN; weights must come from labelled training.

PyTorch operators/checkpoints: https://docs.pytorch.org/docs/stable/nn.html
https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html
Architecture is an SG-2 engineering baseline, not a published accuracy claim.
"""
import time
import cv2
import numpy as np
import torch
from torch import nn

SIZE = (32, 32)


class EyeCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 8, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d((2, 2)))
        self.classifier = nn.Linear(128, 2)

    def forward(self, x):
        return self.classifier(self.features(x).flatten(1))


def preprocess(crop):
    if crop is None or not isinstance(crop, np.ndarray) or crop.size == 0:
        raise ValueError("nonempty eye image required")
    if crop.dtype != np.uint8 or crop.ndim not in (2, 3):
        raise ValueError("expected uint8 grayscale or BGR image")
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    return torch.from_numpy(cv2.resize(gray, SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)/255.0).unsqueeze(0)


class CNNInference:
    def __init__(self, checkpoint, device="cpu"):
        self.device = torch.device(device)
        data = torch.load(checkpoint, map_location=self.device, weights_only=True)
        if data.get("architecture") != "sg2.eye_cnn.v1" or data.get("classes") != ["OPEN", "CLOSED"] or data.get("input_size") != list(SIZE) or data.get("trained") is not True:
            raise ValueError("expected a trained SG-2 v1 checkpoint")
        self.model = EyeCNN().to(self.device)
        self.model.load_state_dict(data["state_dict"])
        self.model.eval()
        self.metadata = {k:v for k,v in data.items() if k != "state_dict"}

    def predict(self, crops):
        if not crops:
            raise ValueError("at least one eye crop required")
        start = time.perf_counter()
        batch = torch.stack([preprocess(c) for c in crops]).to(self.device)
        with torch.inference_mode():
            scores = torch.softmax(self.model(batch), dim=1)[:, 1].cpu().tolist()
        latency = (time.perf_counter()-start)*1000
        return [dict(eye_state="CLOSED" if p >= 0.5 else "OPEN",
                     closed_softmax=p, calibrated=False) for p in scores], latency
