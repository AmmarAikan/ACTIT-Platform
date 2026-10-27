from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def complete(path: Path, epochs: int) -> bool:
    required = [path / "status.json", path / "metrics.json", path / "best_model/model.safetensors", path / "best_model/config.json"]
    if not all(item.is_file() and item.stat().st_size for item in required):
        return False
    status = json.loads((path / "status.json").read_text(encoding="utf-8"))
    return status.get("state") == "completed" and status.get("completed_epochs") == epochs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    args = parser.parse_args()
    experiment = args.experiment_dir.resolve()
    experiment.mkdir(parents=True, exist_ok=True)
    state_path = experiment / "training_state.json"
    state: dict[str, object] = {"state": "running", "started_at": now(), "driver_pid": os.getpid(), "active_model": None, "completed_models": [], "epochs": args.epochs}
    atomic_json(state_path, state)
    try:
        for variant in ("first_subword", "bio_aware"):
            output = experiment / variant
            if complete(output, args.epochs):
                state["completed_models"].append(variant)
                continue
            state.update({"active_model": variant, "active_model_started_at": now()})
            command = [sys.executable, str(Path(__file__).with_name("bert_dnrti_clean_v2.py")), "train",
                       "--variant", variant, "--data-dir", str(args.data_dir), "--output-dir", str(output),
                       "--cache-dir", str(args.cache_dir), "--base-model", "bert-base-cased", "--epochs", str(args.epochs),
                       "--physical-batch-size", "2", "--gradient-accumulation", "8", "--eval-batch-size", "4",
                       "--learning-rate", "0.0001", "--max-length", "120", "--weight-decay", "0.01",
                       "--adam-epsilon", "1e-12", "--max-grad-norm", "1.0", "--seed", "42", "--torch-threads", "4"]
            state["active_command"] = command
            atomic_json(state_path, state)
            subprocess.run(command, check=True)
            if not complete(output, args.epochs):
                raise RuntimeError(f"{variant} did not produce complete artifacts")
            state["completed_models"].append(variant)
            atomic_json(state_path, state)
        state.update({"state": "completed", "active_model": None, "completed_at": now()})
        atomic_json(state_path, state)
    except BaseException as exc:
        state.update({"state": "failed", "failed_at": now(), "error": f"{type(exc).__name__}: {exc}"})
        atomic_json(state_path, state)
        raise


if __name__ == "__main__":
    main()
