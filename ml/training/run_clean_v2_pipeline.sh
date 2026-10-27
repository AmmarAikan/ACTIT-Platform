#!/usr/bin/env bash
set -Eeuo pipefail

project_root=$1
experiment_dir=$2
data_dir=$3
cache_dir=$4
python_bin=$5

cd "${project_root}"
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

"${python_bin}" ml/training/run_clean_v2_driver.py \
  --experiment-dir "${experiment_dir}" \
  --data-dir "${data_dir}" \
  --cache-dir "${cache_dir}" \
  --epochs 4

"${python_bin}" ml/training/finalize_clean_v2.py \
  --experiment-dir "${experiment_dir}"
