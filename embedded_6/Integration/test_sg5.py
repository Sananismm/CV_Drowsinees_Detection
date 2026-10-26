import ast
import math
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "reference_modules" / "sg5_final.py"


def load_sg5_logic():
    """Load SG5's actual decision logic without its plotting/UI imports."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

    required = {
        "STATES",
        "SCORE_INPUTS",
        "C_PARAMS",
        "WARMUP_S",
        "drowsiness_score",
        "MethodC",
    }

    selected = []

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.FunctionDef, ast.ClassDef)):
            if isinstance(node, ast.Assign):
                names = {
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name)
                }
            else:
                names = {node.name}

            if names & required:
                selected.append(node)

    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {"math": math}
    exec(compile(module, str(SOURCE), "exec"), namespace)

    return namespace["MethodC"]


def make_row(t, perclos=0.02, closure=0.0, valid=True):
    return {
        "time_s": float(t),
        "face_valid": valid,
        "perclos": perclos,
        "eye_closure_s": closure,
        "long_blinks": 0,
        "yawn_count": 0,
    }


def main():
    MethodC = load_sg5_logic()

    print("=== SG6 -> SG5 REAL DECISION TEST ===")

    # Scenario 1: Normal driver after warm-up
    sg5 = MethodC()
    state, score, reason = sg5.step(make_row(0))
    state, score, reason = sg5.step(make_row(6))

    assert state == "NORMAL"
    print(f"[PASS] Normal driver: {state}")

    # Scenario 2: Prolonged closure triggers microsleep override
    state, score, reason = sg5.step(
        make_row(7, perclos=0.20, closure=1.6)
    )

    assert state == "DROWSY"
    assert "micro-sleep" in reason
    print(f"[PASS] Microsleep: {state} ({reason})")

    # Scenario 3: Face lost -> preserve previous state
    state, score, reason = sg5.step(
        make_row(8, valid=False)
    )

    assert state == "DROWSY"
    assert "face lost" in reason
    print(f"[PASS] Face lost: {state} ({reason})")

    print("\nRESULT: PASS - REAL SG5 METHOD C EXECUTED")
    print("NOTE: Inputs are controlled test values, not live SG4 data.")


if __name__ == "__main__":
    main()
