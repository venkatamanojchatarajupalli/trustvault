# TrustVault Threat Model

## 1. Project Overview

TrustVault is a secure document-sharing and leak-investigation platform. It uses authentication, role-based access control, protected downloads, permission revocation, and audit trails to help investigate suspicious document access.

## 2. Assets to Protect

- User accounts, credentials, and authentication tokens.
- Private documents and their stored files.
- Document ownership and sharing permissions.
- Audit events and incident reports.
- Document integrity information, including SHA-256 hashes.

## 3. Threat Actors

- Unauthenticated users attempting to access private resources.
- Authenticated viewers attempting administrator-only actions.
- Users attempting to access documents owned or shared with other users.
- Users attempting to bypass revoked permissions.
- Attackers uploading unsupported or excessively large files.

## 4. Threats and Security Controls

| Threat | Security control | Validation |
|---|---|---|
| Unauthorized account access | Password authentication and active-account checks | Authentication tests |
| Duplicate account registration | Unique email enforcement and conflict response | Duplicate-registration test |
| Viewer accessing administrator endpoints | Administrator role dependency | Viewer authorization tests |
| Unauthorized document sharing | Ownership checks and prohibition on self-sharing | Document security tests |
| Unauthorized document download | Ownership and active permission checks | Denied-download test |
| Continued access after permission revocation | Revocation state checked during download | Immediate-revocation test |
| Unsupported file upload | File-extension allowlist | Upload validation test |
| Oversized upload | 10 MiB upload limit and partial-file cleanup | Oversized-upload test |
| Audit history exposure between users | Audit events filtered by the authenticated actor | Audit-isolation test |
| Unauthorized incident creation | Administrator-only incident endpoint | Incident authorization test |
| Incident referencing a nonexistent document | Document existence validation | Missing-document test |

## 5. Document Integrity

TrustVault calculates a SHA-256 digest for uploaded documents. The digest can support later integrity verification and investigation. A matching digest alone does not establish who leaked a document or when a leak occurred.

## 6. Audit and Incident Investigation

Successful logins, document operations, and denied document downloads have audit coverage in the current implementation. Administrator incident reporting records the document, reporting administrator, description, status, and detection timestamp.

Failed-login auditing is not currently included in this stage.

## 7. Known Limitations and Remaining Risks

- Automated tests use an isolated in-memory SQLite database and do not prove production deployment security.
- Production database migration and deployment configuration require separate validation.
- Rate limiting, brute-force protection, and failed-login monitoring require further evaluation.
- Malware scanning and deeper file-content validation are not covered by the current upload tests.
- SHA-256 hashes support integrity checks but do not replace access controls or prove the source of a leak.
- Production secret management, HTTPS, backup recovery, and storage permissions must be reviewed before deployment.

## 8. Test Evidence

The current automated test suite contains 14 passing tests covering authentication, authorization, audit isolation, document sharing, download security, upload validation, and incident reporting.

Command used:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

Latest result: 14 passed, 3 deprecation warnings.

## 9. Security Review Principle

Security controls should be validated through automated tests and deployment checks. Passing tests provide evidence for the tested scenarios, not a guarantee that the application is free of vulnerabilities.
