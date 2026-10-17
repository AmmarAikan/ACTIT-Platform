# ACTIT ↔ MISP production integration final report

- Evidence window: 2026-10-17T22:00Z–2026-10-17T23:00Z
- Worktree: `/opt/cti-platform/worktrees/misp-integration-final-20261017`
- Branch: `codex/misp-integration-final-20261017`
- ACTIT: `https://cti-gateway-vps.tailf2792f.ts.net/`
- MISP: `https://cti-gateway-vps.tailf2792f.ts.net:8443/`
- Production mutation scope: one Event Report on existing MISP event 37
- Secrets: no credential, API key, cookie, or private browser state is recorded here

## Executive conclusion

ACTIT is healthy and remains the authoritative CTI repository. Production MISP
2.5.44 is healthy and contains the governed sharing copy. The original 532
events and 1,535 attributes are real MISP records owned and originated by
`Graduation-CTI-Lab`; they are not evidence that every other MISP data type
should be populated.

The zero counters were mostly truthful. ACTIT currently serializes flat MISP
attributes, not MISP Objects. Existing event data does not establish enough
file identity, endpoint/port, or domain-to-IP relationships to manufacture
non-decorative Objects. Notes and Opinions are unused analyst-collaboration
features. The Galaxy Clusters counter measures locally authored clusters, while
16 ACTIT events already use recognized built-in MITRE ATT&CK Galaxy clusters.
All events are unpublished by design.

The genuine integration gap was Event Reports: ACTIT stores narrative and
provenance, but the MISP serializer dropped them. The branch now previews,
delivers, and read-back-verifies one deterministic, organisation-only Event
Report when a privacy-reviewed External event has meaningful narrative. It
fails closed for Internal, short/decorative, or possible-secret text. Production
event 37 received one curated report through MISP's normal API as the bounded
demonstration. No event, attribute, Object, Galaxy cluster, Note, Opinion, or
publication was fabricated.

## Read-only baseline

### Health, login, version, and access

- ACTIT `GET /api/v1/health`: HTTP 200, `{"status":"ok","database":true}`.
- ACTIT public web root: HTTP 200.
- MISP login page: HTTP 200; authenticated session landed on `Events - MISP`.
- MISP `GET /servers/getVersion`: version 2.5.44; recommended PyMISP 2.5.34.1.
- Authenticated role: `admin` in `Graduation-CTI-Lab`, with publish, analyst
  data, Galaxy editor, and site-admin permissions. No credential value was
  printed or persisted.

### ACTIT MISP configuration and delivery path

Repository/deployment inspection shows:

1. Central Backend and MISP share only the dedicated internal
   `cti-backend-misp` Docker network.
2. Backend uses `MISP_URL=http://cti-misp`, an API key stored outside Git,
   `MISP_ALLOW_HTTP=true` only for the allow-listed same-host alias, and rejects
   other cleartext hosts. Analysts use the separate Tailscale HTTPS endpoint.
3. Admins select candidates in ACTIT's MISP queue, inspect a preview, and send
   at most 20 unique events with `confirm_unpublished=true`.
4. Deterministic UUIDv5 identities prevent duplicate event and attribute
   creation. Repeat delivery searches by UUID, adds only missing attributes,
   reads the event back, and verifies the expected set.
5. The branch extends that same pattern to deterministic Event Reports.

Production endpoints used by the ACTIT client:

- `GET /servers/getVersion`
- `POST /events/restSearch`
- `POST /events/add`
- `POST /attributes/add/{event_id}`
- `GET /events/view/{event_id}`
- added by this branch: `POST /eventReports/add/{event_id}`

ACTIT control endpoints are authenticated. Read-only previews are available to
authenticated users; delivery remains administrator-only in the main workflow.

### Original dashboard and API state

| Area | Original value | Supporting observation |
|---|---:|---|
| Events | 532 | `/events/index.json` and `events/restSearch` |
| Attributes | 1,535 | `/attributes/index.json` and `attributes/restSearch` |
| Objects | 0 | no event `Object` entries; all attributes had `object_id=0` |
| Event reports | 0 | `/eventReports/index.json` |
| Galaxy clusters | 0 | dashboard local-cluster counter |
| Notes | 0 | `/analystData/index/Note.json` |
| Opinions | 0 | `/analystData/index/Opinion.json` |
| Targeting similar orgs | N/A | dashboard widget |
| Published by my org | 0 | all 532 events were unpublished |

Additional state:

- Ownership/origin: all 532 events have `Org=Orgc=Graduation-CTI-Lab`.
- Distribution: 530 events at distribution 0; two controlled synthetic test
  events (532 and 533) at distribution 1. All sharing-group IDs are 0.
- Publication: 532 unpublished, 0 published.
- Analysis: 531 ongoing (`analysis=1`); one controlled test was initial analysis.
- Tags: 531 events have tags; 2,764 tag associations and 45 unique names.
- ATT&CK/Galaxy: 16 events have recognized Galaxy tags and 16 event Galaxy
  blocks. The ATT&CK heatmap contains:
  - Phishing T1566: 9
  - PowerShell T1059.001: 4
  - Scheduled Task/Job T1053: 3
  - Web Protocols T1071.001: 3
  - Brute Force T1110: 1
  - Registry Run Keys / Startup Folder T1547.001: 1
- Attribute types: 778 vulnerability, 329 ip-src, 234 URL, 100 domain, 37
  SHA-1, 26 email-src, 18 MD5, 12 SHA-256, and one controlled ip-dst.
- Only one attribute had `to_ids=true`; it belongs to a controlled validation
  record. Live ACTIT-shared observations remain `to_ids=false` unless evidence
  supports promotion.
- Correlation: 435 attributes had correlation data, covering 180 events, 2,824
  directed links, and 582 unique event pairs. Correlation is functioning even
  though the "Correlations to my org's data" widget is empty because it is
  configured to exclude this organisation's own events and no other org owns
  events here.

## Exact zero/N/A classifications

Each area has exactly one classification.

| Area | Classification | Decision |
|---|---|---|
| Objects = 0 | OPTIONAL FEATURE NOT USED | The serializer is flat-attribute-only. Existing records do not prove file identity or network/domain relationships required for useful Objects. Several observed values are reference or unknown data, so grouping them would add unsupported semantics. |
| Event Reports = 0 | INTEGRATION GAP | ACTIT has privacy-reviewed narrative/provenance fields, but the serializer omitted them. Fixed in the branch and demonstrated once in production. |
| Galaxy Clusters = 0 | EXPECTED | No local clusters are authored. Existing built-in clusters are correctly associated to 16 ACTIT events and appear in the ATT&CK heatmap. |
| Notes = 0 | OPTIONAL FEATURE NOT USED | No analyst-note workflow was demonstrated; creating a note for a counter would be meaningless. |
| Opinions = 0 | OPTIONAL FEATURE NOT USED | No analyst-opinion workflow was demonstrated; no assertion was fabricated. |
| Published by my org = 0 | EXPECTED | ACTIT delivery deliberately defaults to unpublished. Selected events are ongoing and automated ATT&CK mappings require review. |
| Targeting similar orgs = N/A | EXPECTED | The instance contains one originating organisation and the widget requires cross-organisation targeting context. |
| Trending threat actors = empty | OPTIONAL FEATURE NOT USED | ACTIT currently exports ATT&CK technique candidates, not evidence-backed threat-actor cluster assignments. |
| Pew-pew flows = empty | EXPECTED | Current records do not carry validated source-to-destination flow pairs suitable for this visualization. |
| Correlations to my org = empty | EXPECTED | The widget excludes own-org events; all 532 events originate from the same organisation. MISP attribute correlations are independently non-zero. |
| Browser organisation logo 404 | CONFIGURATION ISSUE | The organisation has no configured 48×48 PNG, so MISP requests `/organisations/getOrgLogo/1.json` and receives 404 on the landing/events pages. It is cosmetic and was not changed as CTI enrichment. |

## Curated ACTIT-origin examples

The two October 17 events 532 and 533 were excluded: their comments explicitly
identify synthetic integration-test indicators, and their distribution differs
from the production ACTIT serializer. The following UUIDv5 events carry ACTIT
source-pipeline/provenance tags and extraction comments.

### MISP event 37

- UUID: `b2969d84-b15f-5cc1-aea2-b9531ccef8f6`
- Info: `Vulnerability researchers were repeatedly targeted by trojanised exploits`
- Event date: 2026-08-26
- Timestamp after report addition: 2026-10-17T22:53:04Z
- Origin/owner: `Graduation-CTI-Lab`
- Attributes: 22 (7 vulnerability, 6 domain, 5 SHA-256, 4 URL)
- Distribution/sharing group: 0 / 0
- Published: false; analysis: ongoing
- Provenance tags: external pipeline, Hacker News, medium severity,
  `cti_related`
- Galaxy: built-in MITRE ATT&CK `Web Protocols - T1071.001`
- Review tag: `cti-platform:attack-mapping=analyst-review-required`
- Objects: 0
- Event Reports: one, ID 1, UUID
  `2c6d39d8-8eb4-5338-915e-f5fd619afd46`, distribution 0

### MISP event 38

- UUID: `87e14e53-74c0-5f8b-b004-93335873038b`
- Info: `China-Made ZBT Routers Ship With Two Implants Giving Unauthenticated Attackers Root Access`
- Event date/timestamp: 2026-09-24 / 2026-09-24T04:24:26Z
- Origin/owner: `Graduation-CTI-Lab`
- Attributes: 12 (3 vulnerability, 3 SHA-256, 4 ip-src, 2 domain)
- Distribution/sharing group: 0 / 0
- Published: false; analysis: ongoing
- Provenance tags: external pipeline, RSS, medium severity, `cti_related`
- Galaxy/Objects/Event Reports: 0 / 0 / 0
- Correlation evidence: three attribute links to MISP event 76

### MISP event 519

- UUID: `86e44d4e-226b-54b6-8918-40b608eda227`
- Info: `13 Malicious Packagist Packages Target Unpatched iPhones to Steal Crypto Wallet Seeds`
- Event date/timestamp: 2026-09-24 / 2026-09-24T23:35:16Z
- Origin/owner: `Graduation-CTI-Lab`
- Attributes: 6 (5 vulnerability, 1 domain)
- Distribution/sharing group: 0 / 0
- Published: false; analysis: ongoing
- Provenance tags: external pipeline, RSS, low severity, `cti_related`
- Galaxy: built-in MITRE ATT&CK `Web Protocols - T1071.001`
- Review tag: `cti-platform:attack-mapping=analyst-review-required`
- Objects/Event Reports: 0 / 0

## Changes made

### Live production MISP

One normal MISP API mutation was made:

- Added Event Report ID 1 / UUID
  `2c6d39d8-8eb4-5338-915e-f5fd619afd46` to event 37.
- Name: `ACTIT provenance and source context`.
- Distribution: 0.
- Content uses only already visible event facts: ACTIT authority, source tags,
  type/count summary, existing ATT&CK candidate, and handling decisions.
- Read-back confirmed exactly one matching report.
- Event 37 remained unpublished and distribution 0.

No Objects, clusters, Notes, Opinions, attributes, events, or publications were
created. No existing data was deleted. MISP Funnel/Tailscale settings and ACTIT
production data were untouched.

### Branch code

- Generate at most one deterministic Event Report for meaningful,
  privacy-reviewed External narrative.
- Exclude Internal, short/decorative, and possible-secret text.
- Show the proposed report in ACTIT's MISP preview before an admin sends it.
- Add the report through `/eventReports/add/{event_id}` only when its UUID is
  missing.
- Read the event back and fail if report verification does not match.
- Record requested/added/verified report counts in delivery/audit contracts.
- Preserve deterministic event/attribute behavior, RBAC, distribution 0, and
  unpublished defaults.

This branch change is not deployed to ACTIT production by this task. The one
live MISP report was added directly through the normal MISP workflow so that
the feature could be demonstrated without deploying an unreviewed backend.

## Access path for committee members and analysts

### Browser

1. Open `https://cti-gateway-vps.tailf2792f.ts.net:8443/` over the authorised
   Tailscale path and sign in with an assigned MISP account.
2. Use **Event Actions → List Events** to review governed event copies.
3. Open event 37 to see ACTIT provenance tags, attributes, the existing ATT&CK
   Galaxy association, and the Event Report.
4. Use **Event Actions → List Attributes** to search the shared observables and
   pivot through MISP correlations.

The data flow demonstrated by event 37 is:

```text
ACTIT authoritative source record and privacy-reviewed narrative
  -> administrator reviews ACTIT's filtered MISP preview
  -> deterministic, unpublished, organisation-only MISP event
  -> filtered attributes + ACTIT tags + existing Galaxy association
  -> bounded provenance Event Report
  -> MISP search/correlation and analyst collaboration
```

MISP is the selected/shared copy for governed exchange and collaboration. It is
not the ACTIT system of record.

### REST patterns (no key shown)

Analysts/integrations use a dedicated MISP API key in the `Authorization`
header and JSON content negotiation. Relevant read patterns are:

- `GET /servers/getVersion`
- `GET /events/view/{id}`
- `POST /events/restSearch`
- `POST /attributes/restSearch` with `includeCorrelations=true`
- `GET /eventReports/index/event_id:{id}`
- `GET /galaxies/index.json`

Mutation patterns remain governed/admin-controlled:

- `POST /events/add`
- `POST /attributes/add/{event_id}`
- `POST /eventReports/add/{event_id}`
- publication only through an explicit MISP publish action; ACTIT does not call
  it automatically.

## API and browser verification

API verification after enrichment:

- Login and `servers/getVersion`: successful.
- Dashboard widget export: successful.
- Events/list and attributes/list JSON: 532 / 1,535.
- Event 37 JSON: report, Galaxy, tags, attributes, distribution, and unpublished
  state read back successfully.
- Correlation restSearch: 435 correlated attributes and 582 unique event pairs.

Headless Chromium verification used an in-memory browser context and persisted
no cookies or screenshots:

| Page | HTTP/title | Result |
|---|---|---|
| Dashboard | 200 / `Dashboard - MISP` | rendered |
| Event Actions → List Events | 200 / `Events - MISP` | rendered |
| Event Actions → List Attributes | 200 / `Attributes - MISP` | rendered |
| Event 37 | 200 / `Event #37 - MISP` | title, report, and ATT&CK cluster visible |

JavaScript page exceptions: 0. Network transport failures: 0. Two browser
console resource errors remain because the optional organisation-logo endpoint
returns 404 on the landing/events pages. This is the configuration issue listed
above; zero console errors was therefore not truthfully achieved.

## Tests

Passed:

- six focused MISP serialization/delivery tests, including deterministic report
  mapping, create/read-back verification, repeat-share idempotency, attributes,
  unpublished behavior, and ATT&CK tags;
- two focused backend API tests covering candidate/batch behavior, durable
  outcomes, viewer/analyst/admin RBAC, safe failures, and preview behavior;
- backend compile check for the changed modules;
- frontend TypeScript lint;
- 16 focused MISP/intelligence frontend tests.

The local test environment initially lacked the declared `stix2` package; it
was installed only in an isolated temporary virtual environment before the API
tests. Frontend dependencies and browser tooling were installed only in local
ignored/temporary locations.

## Rollback

### Live Event Report

Use an authorised MISP administrator account to delete Event Report ID 1 from
event 37 through the Event Report controls, or call the normal MISP endpoint
`POST /eventReports/delete/1`. Prefer MISP's normal soft-delete behavior. Then
verify:

- `/eventReports/index.json` returns zero active reports;
- event 37 still has UUID `b2969d84-b15f-5cc1-aea2-b9531ccef8f6`;
- its 22 attributes, tags, Galaxy association, distribution 0, and unpublished
  state are unchanged.

### Branch code

Revert the task commit before deployment. There is no database migration and no
state conversion. Production ACTIT was not deployed from this branch.

## Security notes

- Credentials were read only from the supplied environment variables.
- No password, key, cookie, authenticated HTML, screenshot, or raw browser
  profile was written to the repository or evidence directory.
- No secret appeared in command output or this report.
- The backend still returns exception classes rather than upstream secrets.
- Event Report generation is External-only, bounded, privacy-gated, and rejects
  text in which the approved detector finds a possible secret.
- Distribution remains organisation-only; publication remains opt-in.
- The two synthetic distribution-1 test events were identified but not changed
  or deleted.
- Tailscale, Funnel, MISP networking, Docker volumes, and ACTIT data were not
  modified.

## Final dashboard/API counts

| Area | Final value | Change |
|---|---:|---:|
| Events | 532 | 0 |
| Attributes | 1,535 | 0 |
| Objects | 0 | 0 |
| Event reports | 1 | +1 meaningful report |
| Galaxy clusters | 0 | 0 local clusters; 16 event associations remain |
| Notes | 0 | 0 |
| Opinions | 0 | 0 |
| Targeting similar orgs | N/A | unchanged |
| Published by my org | 0 | unchanged |

The final state is defensible: one real provenance/handling report was added to
an existing ACTIT-originated event, while every zero that lacks a supported use
case remains zero.
