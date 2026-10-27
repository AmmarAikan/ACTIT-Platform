from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    os.environ.get("ACTIT_PROJECT_ROOT", str(Path(__file__).resolve().parents[2]))
).resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402
from transformers import AutoModelForTokenClassification, AutoTokenizer  # noqa: E402

from ml.common.dnrti import BioSplit, build_label_map, read_dnrti_splits  # noqa: E402
from ml.common.metrics import detailed_entity_metrics, detailed_token_metrics  # noqa: E402


DISPLAY_NAMES = {
    "first_subword": "DNRTI-BERT First-Subword Supervision",
    "bio_aware": "DNRTI-BERT BIO-Aware Subword Propagation",
}
INTERNAL_IDS = {"first_subword": "clean_v1_first_subword", "bio_aware": "clean_v1_bio_aware"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parameter_fingerprint(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(str(tuple(value.shape)).encode("ascii"))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def set_determinism(seed: int, threads: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)


def continuation_label(label: str) -> str:
    if label.startswith("B-"):
        return f"I-{label[2:]}"
    return label


class EncodedNerDataset(Dataset):
    def __init__(
        self,
        split: BioSplit,
        tokenizer: Any,
        label2id: dict[str, int],
        max_length: int,
        variant: str,
    ) -> None:
        encoded = tokenizer(
            split.tokens,
            is_split_into_words=True,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )
        loss_labels: list[list[int]] = []
        word_labels: list[list[int]] = []
        for batch_index, labels in enumerate(split.labels):
            word_ids = encoded.word_ids(batch_index=batch_index)
            previous: int | None = None
            item_loss: list[int] = []
            item_words: list[int] = []
            for word_id in word_ids:
                if word_id is None:
                    item_loss.append(-100)
                    item_words.append(-100)
                    previous = word_id
                    continue
                label = labels[word_id]
                first_piece = word_id != previous
                item_words.append(label2id[label] if first_piece else -100)
                if first_piece:
                    item_loss.append(label2id[label])
                elif variant == "bio_aware":
                    item_loss.append(label2id[continuation_label(label)])
                else:
                    item_loss.append(-100)
                previous = word_id
            loss_labels.append(item_loss)
            word_labels.append(item_words)
        self.input_ids = encoded["input_ids"]
        self.attention_mask = encoded["attention_mask"]
        self.token_type_ids = encoded.get("token_type_ids")
        self.loss_labels = torch.tensor(loss_labels, dtype=torch.long)
        self.word_labels = torch.tensor(word_labels, dtype=torch.long)

    def __len__(self) -> int:
        return self.input_ids.shape[0]

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        item = {
            "input_ids": self.input_ids[index],
            "attention_mask": self.attention_mask[index],
            "labels": self.loss_labels[index],
            "word_labels": self.word_labels[index],
        }
        if self.token_type_ids is not None:
            item["token_type_ids"] = self.token_type_ids[index]
        return item


def model_inputs(batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {
        key: value
        for key, value in batch.items()
        if key in {"input_ids", "attention_mask", "token_type_ids", "labels"}
    }


def evaluate(
    model: torch.nn.Module,
    dataset: EncodedNerDataset,
    id2label: dict[int, str],
    batch_size: int,
) -> dict[str, object]:
    model.eval()
    true_sequences: list[list[str]] = []
    pred_sequences: list[list[str]] = []
    total_loss = 0.0
    batches = 0
    with torch.no_grad():
        for batch in DataLoader(dataset, batch_size=batch_size, shuffle=False):
            outputs = model(**model_inputs(batch))
            total_loss += float(outputs.loss.item())
            batches += 1
            predictions = outputs.logits.argmax(dim=-1)
            for predicted, expected in zip(predictions, batch["word_labels"]):
                mask = expected != -100
                true_sequences.append([id2label[int(item)] for item in expected[mask]])
                pred_sequences.append([id2label[int(item)] for item in predicted[mask]])
    entities = detailed_entity_metrics(true_sequences, pred_sequences)
    tokens = detailed_token_metrics(true_sequences, pred_sequences)
    return {
        "loss": total_loss / batches if batches else 0.0,
        "entity": entities,
        "token": tokens,
        "sentences": len(true_sequences),
        "evaluated_word_tokens": sum(len(item) for item in true_sequences),
    }


def unique_unseen_test(splits: dict[str, BioSplit]) -> BioSplit:
    train_keys = {tuple(tokens) for tokens in splits["train"].tokens}
    seen: set[tuple[str, ...]] = set()
    tokens: list[list[str]] = []
    labels: list[list[str]] = []
    for item_tokens, item_labels in zip(splits["test"].tokens, splits["test"].labels):
        key = tuple(item_tokens)
        if key in train_keys or key in seen:
            continue
        seen.add(key)
        tokens.append(item_tokens)
        labels.append(item_labels)
    return BioSplit("test_unique_unseen_train", tokens, labels, 0, [])


def save_model_bundle(model: Any, tokenizer: Any, path: Path, provenance: dict[str, object]) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    model.save_pretrained(path, safe_serialization=True)
    tokenizer.save_pretrained(path)
    atomic_json(path / "training_provenance.json", provenance)


def resource_state() -> dict[str, object]:
    memory: dict[str, int] = {}
    with Path("/proc/meminfo").open("r", encoding="utf-8") as handle:
        for line in handle:
            key, raw = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                memory[key] = int(raw.strip().split()[0]) * 1024
    status: dict[str, int] = {}
    with Path("/proc/self/status").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(("VmRSS:", "VmHWM:")):
                key, raw = line.split(":", 1)
                status[key] = int(raw.strip().split()[0]) * 1024
    return {
        "pid": os.getpid(),
        "memory": memory,
        "process": status,
        "load_average": list(os.getloadavg()),
    }


def train(args: argparse.Namespace) -> None:
    output = args.output_dir
    status_path = output / "status.json"
    if output.exists() and any(output.iterdir()):
        if status_path.is_file():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if status.get("state") == "completed":
                print(f"{args.variant} already completed; refusing to restart")
                return
        raise SystemExit(f"Refusing to overwrite non-complete output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    set_determinism(args.seed, args.torch_threads)
    started = utc_now()
    status: dict[str, object] = {
        "state": "starting",
        "pid": os.getpid(),
        "variant": args.variant,
        "display_name": DISPLAY_NAMES[args.variant],
        "internal_id": INTERNAL_IDS[args.variant],
        "started_at": started,
        "active_epoch": 0,
        "total_epochs": args.epochs,
        "data_dir": str(args.data_dir.resolve()),
        "base_model": args.base_model,
        "initialization": "fresh pretrained base checkpoint; never a prior ACTIT or experiment fine-tune",
        "checkpoint_paths": [],
    }
    atomic_json(status_path, status)
    try:
        splits = read_dnrti_splits(args.data_dir)
        labels = [sequence for split in splits.values() for sequence in split.labels]
        label2id, id2label = build_label_map(labels)
        if len(label2id) != 27:
            raise RuntimeError(f"Expected exact 27-label BIO map, got {len(label2id)}")
        tokenizer = AutoTokenizer.from_pretrained(
            args.base_model, cache_dir=args.cache_dir, use_fast=True
        )
        model = AutoModelForTokenClassification.from_pretrained(
            args.base_model,
            cache_dir=args.cache_dir,
            num_labels=len(label2id),
            id2label=id2label,
            label2id=label2id,
        )
        initial_fingerprint = parameter_fingerprint(model)
        status.update({
            "state": "training",
            "initial_parameter_sha256": initial_fingerprint,
            "tokenizer_class": tokenizer.__class__.__name__,
            "tokenizer_name_or_path": args.base_model,
            "case_sensitive": bool(getattr(tokenizer, "do_lower_case", False) is False),
            "label_count": len(label2id),
        })
        atomic_json(status_path, status)

        datasets = {
            name: EncodedNerDataset(split, tokenizer, label2id, args.max_length, args.variant)
            for name, split in splits.items()
        }
        unseen_split = unique_unseen_test(splits)
        unseen_dataset = EncodedNerDataset(
            unseen_split, tokenizer, label2id, args.max_length, args.variant
        )
        train_loader_length = math.ceil(len(datasets["train"]) / args.physical_batch_size)
        updates_per_epoch = math.ceil(train_loader_length / args.gradient_accumulation)
        total_updates = updates_per_epoch * args.epochs
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=args.learning_rate,
            weight_decay=args.weight_decay,
            eps=args.adam_epsilon,
        )
        scheduler = torch.optim.lr_scheduler.LambdaLR(
            optimizer,
            lr_lambda=lambda step: max(0.0, 1.0 - (step / total_updates)),
        )
        history: list[dict[str, object]] = []
        best_f1 = -1.0
        best_epoch = 0
        global_step = 0
        provenance = {
            "source_checkpoint": args.base_model,
            "initial_parameter_sha256": initial_fingerprint,
            "variant": args.variant,
            "display_name": DISPLAY_NAMES[args.variant],
            "data_dir": str(args.data_dir.resolve()),
            "configuration": {
                "epochs": args.epochs,
                "physical_batch_size": args.physical_batch_size,
                "gradient_accumulation": args.gradient_accumulation,
                "effective_batch_size": args.physical_batch_size * args.gradient_accumulation,
                "eval_batch_size": args.eval_batch_size,
                "learning_rate": args.learning_rate,
                "max_length": args.max_length,
                "weight_decay": args.weight_decay,
                "adam_epsilon": args.adam_epsilon,
                "max_grad_norm": args.max_grad_norm,
                "seed": args.seed,
            },
        }

        for epoch in range(1, args.epochs + 1):
            status["active_epoch"] = epoch
            status["epoch_started_at"] = utc_now()
            atomic_json(status_path, status)
            generator = torch.Generator().manual_seed(args.seed + epoch)
            loader = DataLoader(
                datasets["train"],
                batch_size=args.physical_batch_size,
                shuffle=True,
                generator=generator,
            )
            model.train()
            optimizer.zero_grad(set_to_none=True)
            losses: list[float] = []
            epoch_started = time.monotonic()
            for batch_index, batch in enumerate(loader, start=1):
                outputs = model(**model_inputs(batch))
                loss = outputs.loss
                losses.append(float(loss.item()))
                (loss / args.gradient_accumulation).backward()
                should_step = batch_index % args.gradient_accumulation == 0 or batch_index == len(loader)
                if should_step:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad(set_to_none=True)
                    global_step += 1
            validation = evaluate(model, datasets["valid"], id2label, args.eval_batch_size)
            micro = validation["entity"]["micro"]
            token = validation["token"]
            epoch_path = output / "model" / f"epoch_{epoch}"
            save_model_bundle(model, tokenizer, epoch_path, {**provenance, "epoch": epoch})
            checkpoint_paths = status["checkpoint_paths"]
            assert isinstance(checkpoint_paths, list)
            checkpoint_paths.append(str(epoch_path.resolve()))
            current_f1 = float(micro["entity_f1"])
            is_best = current_f1 > best_f1
            if is_best:
                best_f1 = current_f1
                best_epoch = epoch
                save_model_bundle(
                    model,
                    tokenizer,
                    output / "best_model",
                    {**provenance, "selected_epoch": epoch, "selection_metric": "validation exact-span entity micro F1"},
                )
            entry = {
                "epoch": epoch,
                "training_loss": sum(losses) / len(losses),
                "validation_loss": validation["loss"],
                "entity_precision": micro["entity_precision"],
                "entity_recall": micro["entity_recall"],
                "entity_f1": current_f1,
                "entity_macro": validation["entity"]["macro"],
                "token": token,
                "elapsed_seconds": time.monotonic() - epoch_started,
                "learning_rate_end": scheduler.get_last_lr()[0],
                "best_checkpoint_so_far": is_best,
                "resource_state": resource_state(),
            }
            history.append(entry)
            atomic_json(output / "training_history.json", history)
            atomic_json(output / "validation.json", validation)
            status.update({
                "completed_epochs": epoch,
                "best_epoch": best_epoch,
                "best_validation_entity_f1": best_f1,
                "last_epoch_completed_at": utc_now(),
                "global_optimizer_steps": global_step,
            })
            atomic_json(status_path, status)
            print(json.dumps({"event": "epoch_completed", "variant": args.variant, **entry}), flush=True)

        save_model_bundle(model, tokenizer, output / "final_model", {**provenance, "epoch": args.epochs})
        del model
        model = AutoModelForTokenClassification.from_pretrained(output / "best_model")
        normal_test = evaluate(model, datasets["test"], id2label, args.eval_batch_size)
        unique_unseen = evaluate(model, unseen_dataset, id2label, args.eval_batch_size)
        metrics = {
            "schema_version": "1.0",
            "model": {
                "variant": args.variant,
                "display_name": DISPLAY_NAMES[args.variant],
                "internal_id": INTERNAL_IDS[args.variant],
                "base_checkpoint": args.base_model,
                "initial_parameter_sha256": initial_fingerprint,
                "best_epoch": best_epoch,
                "best_validation_entity_f1": best_f1,
            },
            "normal_test": normal_test,
            "unique_unseen_test": unique_unseen,
            "unique_unseen_definition": "exact case-sensitive clean test token sequences absent from clean training; first occurrence only",
            "test_used_for_selection_or_tuning": False,
            "completed_at": utc_now(),
        }
        atomic_json(output / "metrics.json", metrics)
        atomic_json(output / "entity_metrics.json", normal_test["entity"])
        atomic_json(output / "token_metrics.json", normal_test["token"])
        atomic_json(output / "per_class_metrics.json", normal_test["entity"]["per_type"])
        atomic_json(output / "unique_unseen_metrics.json", unique_unseen)
        best_weights = output / "best_model" / "model.safetensors"
        status.update({
            "state": "completed",
            "completed_at": utc_now(),
            "active_epoch": args.epochs,
            "best_epoch": best_epoch,
            "best_validation_entity_f1": best_f1,
            "best_model_path": str((output / "best_model").resolve()),
            "best_model_sha256": sha256_file(best_weights),
            "normal_test_entity_f1": normal_test["entity"]["micro"]["entity_f1"],
            "unique_unseen_entity_f1": unique_unseen["entity"]["micro"]["entity_f1"],
        })
        atomic_json(status_path, status)
        print(json.dumps({"event": "training_completed", "status": status}), flush=True)
    except BaseException as exc:
        status.update({"state": "failed", "failed_at": utc_now(), "error": f"{type(exc).__name__}: {exc}"})
        atomic_json(status_path, status)
        raise


def smoke(args: argparse.Namespace) -> None:
    set_determinism(args.seed, args.torch_threads)
    splits = read_dnrti_splits(args.data_dir)
    all_labels = [sequence for split in splits.values() for sequence in split.labels]
    label2id, id2label = build_label_map(all_labels)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, cache_dir=args.cache_dir, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(
        args.base_model,
        cache_dir=args.cache_dir,
        num_labels=len(label2id),
        id2label=id2label,
        label2id=label2id,
    )
    samples = BioSplit(
        "smoke",
        splits["train"].tokens[:2],
        splits["train"].labels[:2],
        0,
        [],
    )
    results: dict[str, object] = {}
    for variant in DISPLAY_NAMES:
        dataset = EncodedNerDataset(samples, tokenizer, label2id, args.max_length, variant)
        evaluated = evaluate(model, dataset, id2label, 2)
        model.train()
        smoke_batch = next(iter(DataLoader(dataset, batch_size=2, shuffle=False)))
        smoke_loss = model(**model_inputs(smoke_batch)).loss
        smoke_loss.backward()
        model.zero_grad(set_to_none=True)
        results[variant] = {
            "sentences": evaluated["sentences"],
            "contract_valid": isinstance(evaluated["entity"]["micro"]["entity_f1"], float),
            "forward_backward_valid": bool(torch.isfinite(smoke_loss).item()),
            "smoke_loss": float(smoke_loss.item()),
            "supervised_subword_positions": int((dataset.loss_labels != -100).sum()),
            "word_metric_positions": int((dataset.word_labels != -100).sum()),
        }
    payload = {
        "completed_at": utc_now(),
        "base_model": args.base_model,
        "fresh_pretrained_load": True,
        "initial_parameter_sha256": parameter_fingerprint(model),
        "tokenizer": tokenizer.__class__.__name__,
        "case_sensitive": bool(getattr(tokenizer, "do_lower_case", False) is False),
        "label_count": len(label2id),
        "data_dir": str(args.data_dir.resolve()),
        "results": results,
    }
    atomic_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    subcommands = root.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", type=Path, required=True)
    common.add_argument("--cache-dir", type=Path, required=True)
    common.add_argument("--base-model", default="bert-base-cased")
    common.add_argument("--max-length", type=int, default=120)
    common.add_argument("--seed", type=int, default=42)
    common.add_argument("--torch-threads", type=int, default=4)
    smoke_parser = subcommands.add_parser("smoke", parents=[common])
    smoke_parser.add_argument("--output-json", type=Path, required=True)
    train_parser = subcommands.add_parser("train", parents=[common])
    train_parser.add_argument("--variant", choices=sorted(DISPLAY_NAMES), required=True)
    train_parser.add_argument("--output-dir", type=Path, required=True)
    train_parser.add_argument("--epochs", type=int, default=4)
    train_parser.add_argument("--physical-batch-size", type=int, default=2)
    train_parser.add_argument("--gradient-accumulation", type=int, default=8)
    train_parser.add_argument("--eval-batch-size", type=int, default=4)
    train_parser.add_argument("--learning-rate", type=float, default=1e-4)
    train_parser.add_argument("--weight-decay", type=float, default=0.01)
    train_parser.add_argument("--adam-epsilon", type=float, default=1e-12)
    train_parser.add_argument("--max-grad-norm", type=float, default=1.0)
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "smoke":
        smoke(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
