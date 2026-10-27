#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="${1:-v1.0.0}"
output_dir="${2:-${project_dir}/release-artifacts}"
model_source="${3:-${project_dir}/ml/experiments/bert_paper_parity/20260924T000911Z/production_bundles/actit-ner-hierarchy-20260926/legacy}"
release_name="ACTIT-${version}"

case "${version}" in
  *[!A-Za-z0-9._-]*|'')
    echo "Invalid version: ${version}" >&2
    exit 1
    ;;
esac

required_model_files=(
  config.json
  model.safetensors
  tokenizer.json
  tokenizer_config.json
)

for filename in "${required_model_files[@]}"; do
  if [[ ! -s "${model_source}/${filename}" ]]; then
    echo "Missing required BERT artifact: ${model_source}/${filename}" >&2
    exit 1
  fi
done

mkdir -p "${output_dir}"
stage_dir="$(mktemp -d "${output_dir}/.${release_name}.stage.XXXXXX")"
cleanup() {
  chmod -R u+w "${stage_dir}" 2>/dev/null || true
  rm -rf -- "${stage_dir}"
}
trap cleanup EXIT

release_root="${stage_dir}/${release_name}"
mkdir -p "${release_root}"

rsync -rltp \
  --exclude='.git' \
  --exclude='.agents/' \
  --exclude='.codex/' \
  --exclude='.codex_old/' \
  --exclude='.idea/' \
  --exclude='.prepared-releases/' \
  --exclude='.release-worktrees/' \
  --exclude='.venv*/' \
  --exclude='release-artifacts/' \
  --exclude='documentation/' \
  --exclude='ml/experiments/' \
  --exclude='ml/experiments_clean_v2/' \
  --exclude='ml/models/dnrti_bert_ner/' \
  --exclude='frontend/node_modules/' \
  --exclude='frontend/dist/' \
  --exclude='data/' \
  --exclude='logs/' \
  --exclude='**/__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.env' \
  "${project_dir}/" "${release_root}/"

mkdir -p "${release_root}/ml/models/dnrti_bert_ner"
rsync -rltp "${model_source}/" "${release_root}/ml/models/dnrti_bert_ner/"

git -C "${project_dir}" rev-parse HEAD > "${release_root}/RELEASE_SOURCE_COMMIT.txt"
git -C "${project_dir}" status --short > "${release_root}/RELEASE_WORKTREE_STATUS.txt"

cat > "${release_root}/RESTORE.md" <<'EOF'
# ACTIT portable restore

This bundle contains the ACTIT source, deployment definitions, dependency lock
files, and the production-compatible ACTIT Legacy BERT runtime artifact. It does
not contain runtime databases, collected CTI data, credentials, caches, virtual
environments, node_modules, or research checkpoints.

## Restore on a new server

1. Install Docker Engine, the Docker Compose plugin, OpenSSL, and CA certificates.
2. Enter the extracted ACTIT directory.
3. Run `bash scripts/generate_fresh_env.sh .`.
4. Add credentials only for the external integrations you intend to enable.
5. Validate with `docker compose config --quiet`.
6. Build with `docker compose build --pull`.
7. Start with `docker compose up -d`.
8. Check with `docker compose ps` and the documented health endpoints.

The build requires internet access to download pinned application dependencies
and the base container images. Keep `.env` private and never add it to source
control or the release archive.
EOF

find "${release_root}" -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  | sed "s#  ${release_root}/#  ${release_name}/#" \
  > "${stage_dir}/SHA256SUMS"

archive_path="${output_dir}/${release_name}.tar.gz"
checksum_path="${archive_path}.sha256"
temp_archive="${stage_dir}/${release_name}.tar.gz"

tar -C "${stage_dir}" -cf - "${release_name}" SHA256SUMS | gzip -1 > "${temp_archive}"
mv "${temp_archive}" "${archive_path}"
(
  cd "${output_dir}"
  sha256sum "$(basename "${archive_path}")" > "$(basename "${checksum_path}")"
)

echo "Created ${archive_path}"
echo "Created ${checksum_path}"
