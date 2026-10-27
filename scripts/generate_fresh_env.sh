#!/usr/bin/env bash
set -euo pipefail

project_dir="${1:-.}"
template_path="${project_dir}/.env.example"
env_path="${project_dir}/.env"

if [[ ! -f "${template_path}" ]]; then
  echo "Missing ${template_path}" >&2
  exit 1
fi

if [[ -e "${env_path}" ]]; then
  echo "Refusing to overwrite existing ${env_path}" >&2
  exit 1
fi

umask 077
cp "${template_path}" "${env_path}"

database_password="$(openssl rand -hex 32)"
jwt_secret="$(openssl rand -hex 48)"
admin_password="$(openssl rand -base64 24 | tr -d '\n')"

sed -i \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${database_password}|" \
  -e "s|^JWT_SECRET=.*|JWT_SECRET=${jwt_secret}|" \
  -e "s|^BOOTSTRAP_ADMIN_PASSWORD=.*|BOOTSTRAP_ADMIN_PASSWORD=${admin_password}|" \
  "${env_path}"

chmod 600 "${env_path}"
unset database_password jwt_secret admin_password

echo "Created ${env_path} with fresh internal secrets (mode 0600)."
echo "Add only the external integration credentials you actually use."
echo "The bootstrap administrator password is stored in ${env_path}; do not commit or share it."
