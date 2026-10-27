"""Strict sample and one-to-one onset metrics for labelled SG5 replays.

Rows represent piecewise-constant intervals [time[i], time[i+1]); the last row
uses the median observed interval unless ``final_dt`` is supplied. UNKNOWN is
an abstention and is counted as an error, never removed to improve accuracy.
Ground truth is only used here, never in the decision engine.
"""

from math import isfinite
from numbers import Real
from statistics import mean, median


STATES = ("NORMAL", "WARNING", "DROWSY")
PREDICTED_STATES = STATES + ("UNKNOWN",)


def _number(value):
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def _samples(times, truth, predicted, final_dt):
    times, truth, predicted = list(times), list(truth), list(predicted)
    if not times or not len(times) == len(truth) == len(predicted):
        raise ValueError("nonempty time, truth and prediction arrays must have equal lengths")
    if any(not _number(t) or t < 0 for t in times):
        raise ValueError("timestamps must be finite nonnegative numbers")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("timestamps must strictly increase")
    if any(s not in STATES for s in truth):
        raise ValueError("ground truth must be NORMAL, WARNING or DROWSY")
    if any(s not in PREDICTED_STATES for s in predicted):
        raise ValueError("invalid predicted state")
    gaps = [b - a for a, b in zip(times, times[1:])]
    if final_dt is None:
        if not gaps:
            raise ValueError("one-row traces require an explicit final_dt")
        final_dt = median(gaps)
    if not _number(final_dt) or final_dt <= 0:
        raise ValueError("final_dt must be finite and positive")
    return times, truth, predicted, gaps + [float(final_dt)]


def _episodes(times, flags, end_time):
    result, start = [], None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        if start is not None and (not flag or i == len(flags) - 1):
            end = times[i] if not flag else end_time
            result.append({"start_s": times[start], "end_s": end})
            start = None
    return result


def _overlap(a, b):
    return a["start_s"] < b["end_s"] and b["start_s"] < a["end_s"]


def _event_metrics(times, truth, predicted, end_time):
    actual = _episodes(times, [s == "DROWSY" for s in truth], end_time)
    alerts = _episodes(times, [s == "DROWSY" for s in predicted], end_time)
    matched_truth, matched_alerts, matches = set(), set(), []
    for gi, episode in enumerate(actual):
        for pi, alert in enumerate(alerts):
            if pi not in matched_alerts and episode["start_s"] <= alert["start_s"] < episode["end_s"]:
                matched_truth.add(gi)
                matched_alerts.add(pi)
                matches.append({"ground_truth_index": gi, "prediction_index": pi,
                                "latency_s": round(alert["start_s"] - episode["start_s"], 9)})
                break
    # Late onsets remain false under the strict protocol. The five-second band
    # is diagnostic only and never increases detected_events or event recall.
    late_matches, late_truth = [], set()
    for pi, alert in enumerate(alerts):
        if pi in matched_alerts:
            continue
        for gi, episode in enumerate(actual):
            if (gi not in matched_truth and gi not in late_truth
                    and episode["end_s"] <= alert["start_s"] <= episode["end_s"] + 5.0):
                late_truth.add(gi)
                late_matches.append({"ground_truth_index": gi, "prediction_index": pi,
                                     "after_end_s": round(alert["start_s"] - episode["end_s"], 9)})
                break
    covered = sum(any(_overlap(episode, alert) for alert in alerts) for episode in actual)
    preexisting = sum(any(alert["start_s"] < episode["start_s"] and _overlap(episode, alert)
                          for alert in alerts) for episode in actual)
    precision = len(matches) / len(alerts) if alerts else None
    recall = len(matches) / len(actual) if actual else None
    f1 = (2 * precision * recall / (precision + recall) if precision + recall else 0.0
          ) if precision is not None and recall is not None else None
    latencies = [match["latency_s"] for match in matches]
    return {
        "ground_truth_events": len(actual), "predicted_events": len(alerts),
        "detected_events": len(matches), "missed_events": len(actual) - len(matches),
        "false_alert_events": len(alerts) - len(matches),
        "late_alert_events": len(late_matches), "covered_events": covered,
        "preexisting_alert_events": preexisting,
        "event_precision": precision, "event_recall": recall, "event_f1": f1,
        "coverage": covered / len(actual) if actual else None,
        "mean_latency_s": mean(latencies) if latencies else None,
        "latencies_s": latencies, "ground_truth": actual, "predicted": alerts,
        "matches": matches, "late_matches": late_matches,
    }


def evaluate_predictions(times, truth, predicted, *, valid=None, final_dt=None,
                         driver_states=None, statuses=None):
    """Evaluate a complete trace; invalid-input rows stay in all denominators.

    ``valid`` describes input availability, not whether a prediction was correct.
    If omitted, UNKNOWN predictions are the only available invalidity signal.
    Episode detection requires a new DROWSY onset within the labelled interval.
    Overlap from an already-active alert is reported separately as coverage.
    """
    times, truth, predicted, durations = _samples(times, truth, predicted, final_dt)
    if valid is None:
        valid = [s != "UNKNOWN" for s in predicted]
    else:
        valid = list(valid)
        if len(valid) != len(times) or any(not isinstance(v, bool) for v in valid):
            raise ValueError("valid must contain one boolean per sample")
    if driver_states is None and all(state != "UNKNOWN" for state in predicted):
        driver_states = predicted
    if driver_states is not None:
        driver_states = list(driver_states)
        if len(driver_states) != len(times) or any(state not in STATES for state in driver_states):
            raise ValueError("driver_states must contain one native driver state per sample")
    if statuses is not None:
        statuses = list(statuses)
        if len(statuses) != len(times) or any(not isinstance(status, str) or not status for status in statuses):
            raise ValueError("statuses must contain one nonempty status string per sample")
    counts = [[sum(g == row and p == column for g, p in zip(truth, predicted))
               for column in PREDICTED_STATES] for row in STATES]
    per_class = {}
    for i, state in enumerate(STATES):
        tp = counts[i][i]
        support = sum(counts[i])
        predicted_count = sum(row[i] for row in counts)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[state] = {"support": support, "tp": tp,
                            "fp": predicted_count - tp, "fn": support - tp,
                            "precision": precision, "recall": recall, "f1": f1}
    drowsy = per_class["DROWSY"]
    return {
        "sample_count": len(times), "duration_s": round(sum(durations), 9),
        "accuracy": sum(g == p for g, p in zip(truth, predicted)) / len(times),
        "macro_f1": mean(value["f1"] for value in per_class.values()),
        "per_class": per_class,
        "confusion": {"rows": list(STATES), "columns": list(PREDICTED_STATES), "counts": counts},
        "drowsy_precision": drowsy["precision"], "drowsy_recall": drowsy["recall"],
        "drowsy_f1": drowsy["f1"],
        "false_drowsy_duration_s": round(sum(dt for dt, g, p in zip(durations, truth, predicted)
                                            if p == "DROWSY" and g != "DROWSY"), 9),
        "invalid_duration_s": round(sum(dt for dt, v in zip(durations, valid) if not v), 9),
        "unknown_duration_s": round(sum(dt for dt, p in zip(durations, predicted) if p == "UNKNOWN"), 9),
        "state_changes": sum(a != b for a, b in zip(predicted, predicted[1:])),
        "evaluated_prediction_changes": sum(a != b for a, b in zip(predicted, predicted[1:])),
        "driver_state_changes": (sum(a != b for a, b in zip(driver_states, driver_states[1:]))
                                 if driver_states is not None else None),
        "availability_status_changes": (sum(a != b for a, b in zip(statuses, statuses[1:]))
                                        if statuses is not None else None),
        "input_availability_changes": sum(a != b for a, b in zip(valid, valid[1:])),
        "events": _event_metrics(times, truth, predicted, times[-1] + durations[-1]),
    }
