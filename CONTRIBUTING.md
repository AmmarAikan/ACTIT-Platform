# Contributing to ACTIT

ACTIT is a collaborative graduation project with explicit component ownership and production-safety boundaries. Focused fixes, tests, and documentation improvements are welcome when they preserve those boundaries.

## Before Starting

1. Read [`AGENTS.md`](AGENTS.md) for component ownership, shared-contract rules, and prohibited cross-team changes.
2. Review the current [README](README.md), architecture documentation under `docs/architecture/`, and relevant operation guide under `docs/operations/`.
3. Search existing issues and pull requests to avoid duplicating active work.
4. Discuss any change to shared contracts, another team's module, database migrations, deployment topology, authentication, or production operations before implementation.

Do not use a contribution to test against production, modify live data, publish operational secrets, or introduce a second implementation of External Sources.

## Development Workflow

Create a focused branch from the current default branch:

```bash
git switch main
git pull --ff-only origin main
git switch -c fix/short-description
```

Keep commits small and task-oriented. Preserve unrelated work and generated evidence. Never commit `.env` files, credentials, private source lists, production data, browser state, database dumps, or generated runtime datasets.

Python 3.11 or newer is supported; Python 3.12 is the project baseline. Follow the setup instructions in the README and use placeholder values from the committed example environment files.

## Validation

Run checks that match the code you changed and report their exact results. The Docker-free External Sources quality gate is:

```bash
bash scripts/run_external_tests.sh
```

Focused backend checks include:

```bash
python -m unittest discover -v
python -m unittest discover -s tests/external_sources -p "test_*.py" -v
python -m compileall backend/app/pipeline/ingestion/external
```

For frontend-only work:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

Do not claim live-source, Docker, browser, or production validation unless it was separately authorized and actually performed. Tests should use sanitized fixtures and must not require live credentials.

## Pull Requests

A pull request should:

- explain the problem, scope, and affected components;
- identify shared contracts or consumers, if any;
- list checks as passed, failed, or not run with the reason;
- document configuration or migration effects;
- include only sanitized evidence; and
- update documentation when behavior or interfaces change.

Maintainers may request a smaller scope or coordination with another component owner before review.

## Licensing and Third-party Material

By submitting original code or documentation, you confirm that you have the right to contribute it for distribution under this repository's [MIT License](LICENSE). Do not add third-party datasets, model artifacts, papers, images, or source code unless their terms permit redistribution and the required attribution is recorded in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Report suspected vulnerabilities through [`SECURITY.md`](SECURITY.md), not a public pull request or issue.
