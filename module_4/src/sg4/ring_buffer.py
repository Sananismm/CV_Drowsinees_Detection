"""Fixed-capacity NumPy ring buffer with O(1) sliding-window running sums.

Every frame stores a small row of integer "credited milliseconds" (e.g. dt if
the eye was valid and closed, else 0). Each named window keeps its own tail
pointer and running sums: a push adds the new row and subtracts rows that
fell out of the window. Each row is added once and removed once, so the cost
per update is O(1) amortised, and several windows (60 s, 30 s, ...) share one
buffer without recomputing anything. Integer sums never drift.
"""
from typing import Dict, Iterable, Sequence

import numpy as np


class _Window:
    __slots__ = ("length_ms", "tail", "sums")

    def __init__(self, length_ms: int, n_cols: int):
        self.length_ms = int(length_ms)
        self.tail = 0                      # sequence number of the oldest row in the window
        self.sums = np.zeros(n_cols, dtype=np.int64)


class RingBuffer:
    def __init__(self, capacity: int, columns: Sequence[str], windows_ms: Dict[str, float]):
        self.capacity = int(capacity)
        self.columns = list(columns)
        self._col = {c: i for i, c in enumerate(self.columns)}
        self.t = np.zeros(self.capacity, dtype=np.int64)
        self.rows = np.zeros((self.capacity, len(self.columns)), dtype=np.int64)
        self.seq = 0                       # total rows ever pushed (next write position)
        self.forced_evictions = 0          # rows dropped because capacity < window (FPS too high)
        self.windows = {name: _Window(ms, len(self.columns)) for name, ms in windows_ms.items()}

    def __len__(self) -> int:
        return min(self.seq, self.capacity)

    def push(self, t_ms: int, values: Iterable[int]) -> None:
        cap = self.capacity
        for w in self.windows.values():    # make room: the slot we overwrite must leave every window
            while self.seq - w.tail >= cap:
                w.sums -= self.rows[w.tail % cap]
                w.tail += 1
                self.forced_evictions += 1
        i = self.seq % cap
        self.t[i] = t_ms
        self.rows[i] = values
        self.seq += 1
        row = self.rows[i]
        for w in self.windows.values():
            w.sums += row
            cutoff = t_ms - w.length_ms    # keep rows with t > now - window
            while w.tail < self.seq and self.t[w.tail % cap] <= cutoff:
                w.sums -= self.rows[w.tail % cap]
                w.tail += 1

    def sum(self, window: str, column: str) -> int:
        return int(self.windows[window].sums[self._col[column]])

    def count(self, window: str) -> int:
        """Number of rows currently inside the window."""
        return self.seq - self.windows[window].tail
