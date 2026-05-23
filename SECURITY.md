# Security Policy

## Supported versions

verify-kit is pre-1.0. Only the latest released minor version is supported with
security fixes. Older minors are not patched — `copier update` to the current
release.

| Version       | Supported          |
| ------------- | ------------------ |
| Latest minor  | :white_check_mark: |
| Anything else | :x:                |

## Reporting a vulnerability

**Please do not file public issues for security problems.** Use one of the
private channels below.

1. **Preferred — GitHub private security advisories:**
   https://github.com/m2moiz/verify-kit/security/advisories/new

   This routes the report to the maintainer privately and gives us a place to
   coordinate a fix and a CVE if one is warranted.

2. **Fallback — email** (for reporters without a GitHub account):
   m.moiz1995@gmail.com

The maintainer typically responds within 7 days. There is no formal SLA — this
is a solo-maintained portfolio project. If you do not get a response within 7
days, ping the email fallback once more before assuming the report was missed.

## What to include

- A description of the vulnerability and the impact you believe it has.
- Steps to reproduce, ideally with a minimal `copier copy` answer-set that
  generates the affected scaffold.
- The verify-kit version (commit hash or tag) you observed the issue on.
- Any suggested mitigation or patch.

## What is out of scope

- **No SLA.** This is a solo-dev portfolio project; best-effort response only.
- **No bug bounty.** There is no monetary reward program.
- **Full GitHub Security Advisory workflow (GHSA assignment, CVE issuance,
  embargoed disclosure coordination)** is deferred post-v0.1 per the project's
  Deferred Ideas list. The private-advisory channel above is the disclosure
  path used in the interim.
- Vulnerabilities in third-party dependencies should be reported upstream
  first; we will track and bump versions as patches land.
