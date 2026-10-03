# SVNIT MIS integration

Jarvis keeps MIS HTTP, parsing, persistence, and agent access behind `MISClient`,
`MISSyncService`, and the Phase E MIS tools. Agents should call tools such as
`mis_sync_profile`, `mis_get_attendance`, and `mis_get_results`; they must not
scrape the MIS site themselves.

Use `/api/mis/*` for SVNIT login and sync. The generic `/api/connectors/*` API
only supports connector types with a registered generic adapter; SVNIT MIS is
not registered there. Existing SVNIT connector settings and encrypted
credentials are copied into `mis_accounts` by the account migration.

## Configuration

Set `CONNECTOR_ENCRYPTION_KEY` to a Fernet key, `SVNIT_MIS_BASE_URL` to the
trusted HTTPS host, and `SVNIT_MIS_CONFIGURATION_JSON` to the WebForms paths
and login field names. For example:

```json
{
  "login_path": "/SVNIT/",
  "logout_path": "/Logout.aspx",
  "session_check_path": "/Student/Profile.aspx",
  "resources": {
    "profile": "/Student/Profile.aspx",
    "attendance": "/Student/Attendance.aspx",
    "results": "/Student/Results.aspx",
    "timetable": "/Student/Timetable.aspx"
  },
  "login_fields": {
    "username": "txt_username",
    "encrypted_password": "hdnEncPwd",
    "captcha": "txtcaptcha"
  },
  "rsa_ciphertext_encoding": "base64"
}
```

Map those paths and field names to the actual SVNIT MIS page. RSA modulus and
exponent values come from each fetched login page. Jarvis uses RSAES-PKCS1-v1_5.
The current SVNIT page uses JSEncrypt, whose `encrypt()` result is Base64, so
configure `rsa_ciphertext_encoding` as `base64`. Verify this against the current login page with
`python -m scripts.validate_mis_login` from the `backend/` directory before
enabling MIS sync. `SVNIT_MIS_BASE_URL` is the HTTPS host origin
(`https://mis.svnit.ac.in`), not the login page URL; configure the login page
path separately as `login_path` in `SVNIT_MIS_CONFIGURATION_JSON`. The API and
validator load the repository-root `.env` independently of the current working
directory. To verify only the live login bootstrap without submitting
credentials, run `python -m scripts.validate_mis_login --check-bootstrap` from
`backend/`; the full validator continues with the interactive captcha and
login flow. The currently verified SVNIT login path is `/SVNIT/`, with username
field `txt_username` and captcha field `txtcaptcha`.
Login diagnostics log submitted field names and a redacted, bounded feedback
excerpt from failed responses; they do not log passwords, captcha answers,
ciphertext, hidden-state values, or raw HTML.

The validation script requires `SVNIT_MIS_BASE_URL`, accepts optional
`SVNIT_MIS_CONFIGURATION_JSON`, `SVNIT_MIS_USERNAME`, and
`SVNIT_MIS_PASSWORD`, and always asks the user to solve the captcha manually.
It prints stage results only and never prints credentials.

## Login and session behavior

`POST /api/mis/login/start?student_id=<id>` fetches the login page and returns a
captcha data URI for the frontend. The user submits the typed captcha, username,
and password to `POST /api/mis/login/complete?student_id=<id>`. Passwords are
RSA-encrypted for the MIS form and credentials are Fernet-encrypted before
PostgreSQL persistence. The login challenge and its session cookies are also
Fernet-encrypted in `mis_login_sessions`, allowing start/complete and sync
requests to reach different API workers without sharing student sessions. Each
operation restores a student-specific `requests.Session` and persists rotated
cookies encrypted. If the MIS session expires, the user starts a new challenge
and solves the captcha again. No automatic captcha solving or plaintext
password or cookie persistence is used.

MIS snapshot metadata is stored with the profile record in
`mis_student_profiles`; apply Alembic migrations before deploying.
