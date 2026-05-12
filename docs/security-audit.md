# Security Audit Report — InfiTrans

> Expert-level security analysis for enterprise translation platform deployment.  
> Audit Date: 2026-05-01 | Platform Version: 0.3.0 (post-hardening)

---

## Executive Summary

InfiTrans is architecturally designed for **air-gapped deployment** — all LLM inference runs locally via Ollama, with zero outbound network calls required. The platform uses JWT authentication, bcrypt password hashing, and S3-compatible object storage with optional encryption at rest.

**Post-hardening status**: 6 critical items from the initial audit have been resolved in this version.

### Risk Matrix (Updated)

| Category | Current State | Risk Level | Status |
|:---------|:-------------|:-----------|:-------|
| Authentication | JWT + bcrypt + **rate limiting** | ✅ **LOW** | Rate limiter added (5/15min) |
| Authorization | Owner-based isolation + **registration control** | ✅ **LOW** | `REGISTRATION_ENABLED` gate |
| Data at Rest | SSE-C available (HTTPS only) | ⚠️ **MEDIUM** | Enable TLS termination |
| Data in Transit | HTTP (dev default) | ⚠️ **HIGH** | Add TLS/reverse proxy |
| Input Validation | File type + **size limit (50MB)** | ✅ **LOW** | `MAX_FILE_SIZE` enforced |
| LLM Security | No code execution | ✅ **LOW** | No action needed |
| Container Security | **Non-root user** + slim base | ✅ **LOW** | `USER appuser` in Dockerfile |
| CORS | **Restricted origins** | ✅ **LOW** | `CORS_ORIGINS` configurable |
| Secret Management | .env file | ⚠️ **MEDIUM** | Use Docker secrets or Vault |

### Changes Since Initial Audit

| Fix | Before | After |
|:----|:-------|:------|
| Rate Limiting | ❌ None | ✅ 5 attempts / 15 min per IP |
| File Size Limit | ❌ None | ✅ 50MB default (`MAX_FILE_SIZE`) |
| CORS | ❌ `allow_origins=["*"]` | ✅ Configurable `CORS_ORIGINS` |
| Container User | ❌ Root | ✅ Non-root `appuser` |
| Registration | ❌ Open | ✅ `REGISTRATION_ENABLED` gate |
| Multi-file Upload | ❌ Single only | ✅ Sequential queue |

---

## 1. Authentication & Session Management

### Current Implementation

| Feature | Implementation | Status |
|:--------|:--------------|:-------|
| Password Hashing | `bcrypt` (native, no passlib) | ✅ Secure |
| Hash Format | `$2b$12$...` (12 rounds) | ✅ OWASP recommended |
| JWT Algorithm | HS256 | ✅ Standard |
| Token Expiry | 7 days | ⚠️ Long for enterprise |
| Token Storage | localStorage (frontend) | ⚠️ XSS vulnerable |
| Rate Limiting | 5 attempts / 15 min per IP | ✅ Implemented |
| Account Lockout | Via rate limiter | ✅ Implemented |
| Password Policy | Min 6 chars (change-password) | ⚠️ Weak |
| MFA | Not implemented | ❌ Missing |

### Security Analysis

**Strengths:**
- `bcrypt` with 12 rounds provides strong password hashing (~250ms per hash)
- Direct bcrypt usage (no passlib) eliminates dependency version conflicts
- Password verification wrapped in try/except prevents hash corruption crashes
- **Rate limiter** tracks failed login attempts per IP with sliding window

**Weaknesses:**
- `SECRET_KEY` default value `super-secret-key-please-change-in-prod` — must be rotated
- 7-day JWT expiry is too long for enterprise; recommend 1-4 hours + refresh tokens
- localStorage token storage is vulnerable to XSS; httpOnly cookies preferred

### Remaining Recommendations

```python
# 1. Generate strong SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# 2. Reduce token expiry (auth.py)
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 4  # 4 hours instead of 7 days
```

---

## 2. Authorization & Access Control

### Current Implementation

| Feature | Status | Detail |
|:--------|:-------|:-------|
| Owner Isolation | ✅ Implemented | Jobs/glossary filtered by `owner_id` |
| Role-Based Access | ⚠️ Partial | `role` field exists, enforced on reset-password |
| Admin Functions | ⚠️ Basic | Admin can reset passwords |
| Registration Control | ✅ Implemented | `REGISTRATION_ENABLED` env var |

### Analysis

- **Registration Gate**: `/api/auth/register` now checks `settings.REGISTRATION_ENABLED` — returns HTTP 403 when disabled
- **Owner Isolation**: Download, job listing, and glossary all filter by `owner_id` — **correct** ✅
- **Admin Role**: The `role` field is enforced on `/api/auth/reset-password` (admin-only)

### Remaining Recommendations

1. Implement full RBAC middleware: `Depends(require_role("admin"))` for admin endpoints
2. Add invite code system for controlled user onboarding

---

## 3. Data Protection

### Data at Rest

| Storage | Encryption | Status |
|:--------|:----------|:-------|
| MinIO Objects | SSE-C (AES-256) | ⚠️ Requires HTTPS |
| SurrealDB | None (filesystem) | ⚠️ Unencrypted |
| Docker Volume | Host filesystem | ⚠️ Depends on host |

### Data in Transit

| Connection | Encryption | Status |
|:-----------|:----------|:-------|
| Browser → FastAPI | HTTP (default) | ❌ Plaintext |
| FastAPI → Ollama | HTTP (internal) | ⚠️ OK for Docker network |
| FastAPI → SurrealDB | WS (internal) | ⚠️ OK for Docker network |
| FastAPI → MinIO | HTTP (internal) | ⚠️ OK for Docker network |

### Recommendations

1. **TLS Termination**: Deploy nginx/Caddy reverse proxy with Let's Encrypt
2. **Docker Network Isolation**: Use `internal: true` for backend services

---

## 4. Input Validation & File Security

### File Upload Security

| Check | Implementation | Status |
|:------|:--------------|:-------|
| File Type Validation | Extension-based whitelist | ✅ Implemented |
| Filename Sanitization | Strips `/` and `\` | ✅ Basic |
| Path Traversal Prevention | UUID prefix + flat storage | ✅ Secure |
| File Size Limit | `MAX_FILE_SIZE` (50MB default) | ✅ Implemented |
| Content-Type Validation | Not checked | ⚠️ Extension only |
| Antivirus Scanning | Not implemented | ❌ Missing |

### XML Processing Security

| Vulnerability | Protection | Status |
|:-------------|:----------|:-------|
| XML External Entity (XXE) | `xml.etree` (no DTD by default) | ✅ Safe |
| XML Bomb (Billion Laughs) | `xml.etree` parser limits | ✅ Safe |
| XSLT Injection | No XSLT processing | ✅ N/A |
| ZIP Bomb | Limited by `MAX_FILE_SIZE` | ✅ Mitigated |

---

## 5. LLM Security

| Threat | Risk | Mitigation |
|:-------|:-----|:-----------|
| Prompt Injection | LOW | Controlled prompts, no user text in system prompt |
| Data Exfiltration via LLM | NONE | Ollama runs locally, no outbound calls |
| Code Execution | NONE | System never generates or executes code |
| Model Poisoning | LOW | User controls model selection |
| Hallucinated Output | MEDIUM | RALPH Loop + Source Leak Detector |

**Air-Gap Capability**: Ollama runs entirely locally. No internet connection required after initial model download.

---

## 6. Container Security

### Dockerfile Analysis

| Practice | Status | Detail |
|:---------|:-------|:-------|
| Multi-stage build | ✅ | Separates build from runtime |
| Slim base image | ✅ | `python:3.13-slim` |
| Non-root user | ✅ Implemented | `USER appuser` |
| Read-only filesystem | ❌ Not set | Container FS is writable |
| Security scanning | ❌ Not configured | No Trivy/Snyk in CI |
| Health checks | ✅ | HTTP health endpoint |

### Remaining Recommendations

```yaml
# docker-compose.yml — add read-only FS
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
```

---

## 7. Secret Management

### Current Secrets Inventory

| Secret | Location | Rotation | Risk |
|:-------|:---------|:---------|:-----|
| `SECRET_KEY` | `.env` | Manual | **HIGH** if default |
| `SURREALDB_PASS` | `.env` + docker-compose | Manual | MEDIUM |
| `MINIO_SECRET_KEY` | `.env` + docker-compose | Manual | MEDIUM |
| `STORAGE_ENCRYPTION_KEY` | `.env` | Manual | LOW |

### Recommendations

Use Docker secrets for production:
```bash
# Generate strong secrets
python3 -c "import secrets; print(secrets.token_urlsafe(64))" > secrets/jwt_secret.txt
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/surreal_pass.txt
```

---

## 8. CORS Configuration

### Current State (Fixed)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,     # ✅ Configurable
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

Default: `http://localhost:8000,http://127.0.0.1:8000`

Configure via: `CORS_ORIGINS=https://yourdomain.com` in `.env`

---

## 9. Enterprise Translation Standard Compliance

### ISO 17100:2015 (Translation Services)

| Requirement | InfiTrans Status | Gap |
|:------------|:----------------|:----|
| Source text analysis | ✅ Auto-detect + domain routing | — |
| Terminology management | ✅ Glossary enforcement | — |
| Translation memory | ✅ SurrealDB cache | — |
| Quality assurance | ✅ Confidence scoring + RALPH | — |
| Human review process | ✅ Bilingual editor + XLIFF | — |
| Revision/proofreading | ⚠️ Single review only | Add multi-reviewer workflow |
| Format preservation | ✅ Deterministic ZIP reconstruction | — |
| Traceability | ✅ Job history + duration tracking | Add audit log |

### XLIFF 2.1 / OASIS Standard

| Feature | Status |
|:--------|:-------|
| XLIFF 1.2 export/import | ✅ Full support |
| XLIFF 2.1 export/import | ✅ Full support |
| Inline tag mapping | ✅ `<bpt>`/`<ept>` (1.2), `<pc>`/`<ph>` (2.1) |
| CAT tool interop (Trados, memoQ) | ✅ Tested |

### GDPR / Data Privacy

| Requirement | Status | Detail |
|:------------|:-------|:-------|
| Data minimization | ✅ | Only stores translation-relevant data |
| Right to deletion | ⚠️ Partial | Auto-retention policy, no user self-delete |
| Data portability | ✅ | XLIFF export for all data |
| Encryption at rest | ⚠️ Optional | SSE-C available (HTTPS required) |
| Air-gap capability | ✅ | Full local deployment, no cloud dependency |
| Audit trail | ⚠️ Partial | Job history exists, no detailed event log |

### SOC 2 Readiness

| Control | Status | Action Required |
|:--------|:-------|:----------------|
| Access Control | ✅ JWT + rate limiting | Add MFA |
| Encryption | ⚠️ Partial | Enable TLS everywhere |
| Logging | ⚠️ Application logs only | Add structured audit logging |
| Change Management | ✅ Git-based | — |
| Incident Response | ❌ Not defined | Create IR playbook |
| Backup & Recovery | ⚠️ Volume-based | Add automated backup schedule |

---

## 10. Hardening Checklist

### ✅ Completed (this release)

- [x] File upload size limit (`MAX_FILE_SIZE=50MB`)
- [x] CORS restricted to specific origins (`CORS_ORIGINS`)
- [x] Login rate limiting (5 attempts / 15 min per IP)
- [x] Non-root container user (`USER appuser`)
- [x] Registration control (`REGISTRATION_ENABLED`)
- [x] Multi-file upload support

### Pre-Production (Must Do)

- [ ] Change `SECRET_KEY` to cryptographically random value
- [ ] Change SurrealDB credentials from `root`/`root`
- [ ] Change MinIO credentials from `minioadmin`/`minioadmin`
- [ ] Deploy behind TLS reverse proxy (nginx/Caddy)

### Post-Production (Should Do)

- [ ] Enable SSE-C encryption (requires HTTPS to MinIO)
- [ ] Add login audit logging
- [ ] Set up automated backup for SurrealDB + MinIO
- [ ] Run container image scanning (Trivy/Snyk)
- [ ] Isolate backend services in Docker internal network

### Enterprise (Nice to Have)

- [ ] Implement MFA (TOTP)
- [ ] Add RBAC with admin panel
- [ ] Integrate with LDAP/SSO (SAML/OIDC)
- [ ] Add ClamAV file scanning
- [ ] Implement structured audit event log
- [ ] Add Prometheus metrics endpoint
