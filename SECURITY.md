# Security Policy

ACTIT is a graduation-project prototype that processes security data and integrates with external services. Security reports are welcome, but this repository does not provide a production support SLA or a bug-bounty program.

## Supported Code

Security fixes target the current `main` branch. Historical branches, local experiments, and old deployment snapshots are not supported releases. Check the repository's current documentation before evaluating behavior because architecture and deployment boundaries may change.

## Report a Vulnerability Privately

Use GitHub's [private vulnerability reporting form](https://github.com/AmmarAikan/ACTIT-Platform/security/advisories/new). Do not open a public issue for a vulnerability that could expose credentials, private data, infrastructure details, or a working exploit.

Include only the information needed to reproduce and assess the issue:

- affected component and commit;
- impact and prerequisites;
- minimal reproduction steps using synthetic data;
- suggested mitigation, if known; and
- whether the issue may affect a deployed instance.

Never include real credentials, tokens, private keys, personal data, production database contents, internal host details, or unredacted logs. If a secret may already be exposed, revoke or rotate it through the appropriate service rather than sending its value in the report.

## Safe Research Boundaries

- Test a local instance that you control with synthetic data.
- Do not probe the public ACTIT or MISP deployments without explicit written authorization for that specific test.
- Do not access, modify, retain, or disclose other people's data.
- Avoid denial of service, persistence, social engineering, and automated traffic that could affect shared infrastructure.
- Give maintainers a reasonable opportunity to investigate and remediate before public disclosure.

## Non-sensitive Bugs

Use a regular GitHub issue for ordinary defects that have no security or privacy impact. Redact operational details and confirm that the report contains no secrets before submitting it.
