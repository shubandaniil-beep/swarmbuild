# Security, Admin Access, Honeypot Policy

Internal document. This is not customer-facing copy.

## What Is Allowed

Defensive cybersecurity work for SwarmBuild AI is allowed when the goal is to
protect the user's own application, infrastructure, users, and API keys.

Allowed examples:

- hardening login and admin access;
- password hashing and secret encryption;
- rate limiting;
- audit logs;
- alerting on suspicious behavior;
- fake admin honeypot routes for detection;
- decoy records that do not expose real secrets;
- security reports and deployment checklists;
- safe red-team tests against this local app.

Not allowed and not useful for the product:

- stealing real credentials;
- phishing real users;
- malware, persistence, exfiltration, credential dumping;
- bypassing third-party systems;
- instructions for unauthorized access;
- logging third-party passwords entered by mistake.

## Passwords: Hash, Do Not Encrypt

Do not "encrypt passwords" in a reversible form.

Correct pattern:

```text
password -> random per-user salt -> slow password hash -> stored hash
```

Current implementation:

- PBKDF2-HMAC-SHA256;
- random per-password salt;
- 200,000 iterations;
- constant-time comparison.

Production target:

- Argon2id as the preferred password hash;
- keep PBKDF2 verification for old accounts during migration;
- rehash to Argon2id on successful login;
- admin MFA before production launch.

SSH is a transport/access mechanism, not a password storage mechanism.

Correct SSH use:

- Ed25519 SSH keys for server access;
- no password SSH login on production servers;
- separate deploy key with least privilege;
- rotate keys when team members leave;
- store server private keys outside the app repository.

## API Keys

Provider API keys are secrets and must be treated differently from passwords:

- API keys need reversible encryption because the backend must send them to the
  provider at call time.
- Current implementation uses AES-256-GCM.
- The key is derived from `ENCRYPTION_SECRET`.
- API responses and UI only expose masks like `sk-...f604`.
- Plaintext keys should exist only in memory during the provider call.

Operational rule:

```text
No plaintext provider key in logs, frontend state, generated artifacts,
browser localStorage, screenshots, or support messages.
```

## Admin Access Model

Current model:

- `/admin-login` has a separate admin login endpoint;
- admin routes require `role == "admin"`;
- sessions use HttpOnly cookies;
- logout increments token version and revokes old tokens;
- login attempts are rate-limited by IP and email;
- public registration has fingerprint/IP anti-abuse checks.

Production additions:

- admin MFA;
- session list and revoke-all;
- trusted devices;
- optional IP allowlist for founder/admin accounts;
- admin audit feed with export;
- alert on provider key changes, tariff changes, model enable/disable changes,
  and forced project packaging.

## Honeypot Admin Design

A fake admin route can be useful as a defensive sensor. It must be built as a
trap, not as a phishing system.

Allowed design:

```text
/admin-old
/wp-admin
/administrator
/internal-panel
```

Behavior:

- show a believable but fake login screen;
- never use real admin components;
- never connect to real admin APIs;
- never reveal whether an email exists;
- never store the raw password;
- store only safe telemetry:
  - timestamp;
  - IP or trusted proxy IP;
  - user agent;
  - path;
  - email hash, not email plaintext when possible;
  - password length and strength category, not the password itself;
  - browser fingerprint hash;
  - request id.

Response:

- always return generic failure;
- add progressive delay;
- rate-limit aggressively;
- flag the source in admin logs;
- optionally block project creation from the same fingerprint/IP for a short
  period when abuse is obvious.

Do not:

- collect real passwords;
- forward credentials anywhere;
- reuse entered data to try logging in;
- expose real admin UI after honeypot login;
- create a vulnerability just to catch attackers.

## Honeypot Implementation Sketch

Backend:

```text
POST /api/security/honeypot-login
  normalize input
  hash email/fingerprint
  classify attempt
  log event: honeypot_attempt
  return 401 generic
```

Frontend:

```text
/admin-old/page.tsx
  fake login form
  posts only to honeypot endpoint
  no real session cookie
```

Database:

```text
security_events
  id
  event_type
  ip
  user_agent
  fingerprint_hash
  email_hash
  password_length
  password_category
  path
  created_at
```

Admin UI:

```text
/admin/security
  suspicious attempts
  top IPs/fingerprints
  recent honeypot hits
  block/unblock controls
```

## Safe Logging Rules

Never log:

- plaintext password;
- plaintext provider API key;
- full auth token;
- full session cookie;
- raw generated prompt;
- private routing prompt;
- generated artifact before secret redaction.

Allowed:

- masked key;
- token hash prefix;
- email hash or admin-visible email where operationally required;
- safe provider error with secrets redacted;
- request id;
- project id;
- phase key;
- model display name.

## Security Copy For Customers

Use simple customer-safe language:

```text
SwarmBuild protects project generation with account access controls, provider
key encryption, abuse monitoring, and automatic artifact redaction before
download.
```

Do not say:

```text
Here is exactly how our model router works.
Here are the prompt roles and provider priorities.
Here is the honeypot route.
Here is the internal admin path strategy.
```
