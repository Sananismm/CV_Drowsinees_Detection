"""Per-update latency and memory of the SG-4 engine. Runs unchanged on the Jetson.

    python module_4/tools/benchmark.py                 # 12,000 frames of the noisy scenario
    python module_4/tools/benchmark.py --frames 30000 --csv results/benchmark_pc.csv

Times every push() (frames that also emit a 10 Hz vector are reported separately)
with time.perf_counter. Memory: tracemalloc peak of the engine's Python/NumPy
allocations, plus the process max RSS. Needs only numpy + pyyaml.
"""
import argparse
import gc
import platform
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mock_stream  # noqa: E402
from sg4.engine import TemporalEngine  # noqa: E402


def _max_rss_mb():
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / 1e6 if sys.platform == "darwin" else r / 1e3   # bytes on macOS, KiB on Linux
    except ImportError:
        return float("nan")


def make_records(n_frames):
    """Repeat the noisy mock, shifting timestamps, until n_frames records exist."""
    base, gt = mock_stream.generate("noisy")
    period = gt["duration_ms"]
    out, k = [], 0
    while len(out) < n_frames:
        for r in base:
            r = dict(r, timestamp_ms=r["timestamp_ms"] + k * period)
            out.append(r)
            if len(out) == n_frames:
                break
        k += 1
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", type=int, default=12000)
    ap.add_argument("--csv", help="append a result row to this CSV")
    a = ap.parse_args(argv)

    records = make_records(a.frames)
    engine = TemporalEngine()
    for r in records[:300]:                         # warm-up (imports, first allocations)
        engine.push(r)
    engine = TemporalEngine()
    gc.collect()
    tracemalloc.start()
    t_all, t_out = [], []
    for r in records:
        t0 = time.perf_counter()
        o = engine.push(r)
        dt = (time.perf_counter() - t0) * 1000.0
        (t_out if o is not None else t_all).append(dt)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    every = np.array(t_all + t_out)
    rows = [("all updates", every), ("frame only", np.array(t_all)), ("frame + 10 Hz output", np.array(t_out))]
    host = "%s %s, Python %s, NumPy %s" % (platform.system(), platform.machine(), platform.python_version(),
                                           np.__version__)
    print("SG-4 benchmark: %d frames | %s" % (len(records), host))
    print("%-22s %8s %10s %10s %10s" % ("", "n", "mean ms", "p95 ms", "max ms"))
    for name, x in rows:
        print("%-22s %8d %10.4f %10.4f %10.4f" % (name, x.size, x.mean(), np.percentile(x, 95), x.max()))
    print("engine peak allocations (tracemalloc): %.2f MB" % (peak / 1e6))
    print("process max RSS: %.1f MB" % _max_rss_mb())
    print("targets: < 2 ms per update, < 50 MB")
    if a.csv:
        new = not Path(a.csv).exists()
        with open(a.csv, "a") as f:
            if new:
                f.write("host,frames,mean_ms,p95_ms,max_ms,out_mean_ms,out_p95_ms,peak_alloc_mb,max_rss_mb\n")
            f.write('"%s",%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.2f,%.1f\n' % (
                host, len(records), every.mean(), np.percentile(every, 95), every.max(),
                np.mean(t_out), np.percentile(t_out, 95), peak / 1e6, _max_rss_mb()))


if __name__ == "__main__":
    main()
