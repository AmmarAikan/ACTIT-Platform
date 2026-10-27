from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


MODELS = ("first_subword", "bio_aware")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected an object in {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", type=Path, required=True)
    args = parser.parse_args()
    experiment = args.experiment_dir.resolve()
    dataset = read_json(experiment / "dataset_construction.json")
    models: dict[str, dict] = {}
    for name in MODELS:
        directory = experiment / name
        status = read_json(directory / "status.json")
        metrics = read_json(directory / "metrics.json")
        weights = directory / "best_model/model.safetensors"
        normal = metrics["normal_test"]
        unseen = metrics["unique_unseen_test"]
        models[name] = {
            "state": status.get("state"),
            "best_epoch": metrics["model"]["best_epoch"],
            "validation_entity_f1": metrics["model"]["best_validation_entity_f1"],
            "test_entity_f1": normal["entity"]["micro"]["entity_f1"],
            "test_token_accuracy": normal["token"]["token_accuracy"],
            "unique_unseen_entity_f1": unseen["entity"]["micro"]["entity_f1"],
            "evaluated_test_sentences": normal["sentences"],
            "artifact_sha256": sha256(weights),
        }
    primary = models["first_subword"]
    fallback = models["bio_aware"]
    gates = {
        "dataset_integrity_all_passed": dataset.get("all_quality_gates_passed") is True,
        "both_training_runs_completed": all(value["state"] == "completed" for value in models.values()),
        "both_artifacts_present": all((experiment / name / "best_model/model.safetensors").is_file() for name in MODELS),
        "primary_test_f1_at_least_0_75": primary["test_entity_f1"] >= 0.75,
        "fallback_test_f1_at_least_0_75": fallback["test_entity_f1"] >= 0.75,
        "primary_token_accuracy_at_least_0_90": primary["test_token_accuracy"] >= 0.90,
        "fallback_token_accuracy_at_least_0_90": fallback["test_token_accuracy"] >= 0.90,
        "primary_unique_unseen_f1_at_least_0_73": primary["unique_unseen_entity_f1"] >= 0.73,
        "fallback_unique_unseen_f1_at_least_0_73": fallback["unique_unseen_entity_f1"] >= 0.73,
        "primary_outperforms_fallback_entity_f1": primary["test_entity_f1"] > fallback["test_entity_f1"],
    }
    all_passed = all(gates.values())
    decision = "eligible_for_runtime_validation" if all_passed else "retain_legacy_bert"
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_policy": dataset.get("policy_version"),
        "models": models,
        "quality_gates": gates,
        "all_training_and_scientific_gates_passed": all_passed,
        "decision": decision,
        "production_changed": False,
        "decision_scope": "Runtime compatibility, bounded CPU benchmark, integration, fallback, and deployment approval remain separate before production promotion.",
    }
    (experiment / "final_decision.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# تقرير تدريب وتقييم DNRTI Clean-v2", "",
        f"- القرار: **{decision}**", "- لم يُغيّر الإنتاج.", "",
        "## النتائج", "", "| النموذج | أفضل حقبة | Validation F1 | Test F1 | Token accuracy | Unique-unseen F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in MODELS:
        value = models[name]
        lines.append(f"| {name} | {value['best_epoch']} | {value['validation_entity_f1']:.6f} | {value['test_entity_f1']:.6f} | {value['test_token_accuracy']:.6f} | {value['unique_unseen_entity_f1']:.6f} |")
    lines.extend(["", "## بوابات القبول", ""])
    lines.extend(f"- {key}: {'PASS' if passed else 'FAIL'}" for key, passed in gates.items())
    lines.extend(["", "حتى عند نجاح هذه البوابات، يلزم تحقق runtime وCPU والتكامل والـfallback وموافقة نشر منفصلة قبل الاستبدال الإنتاجي.", ""])
    (experiment / "FINAL_TRAINING_REPORT_AR.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
