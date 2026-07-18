# Security Policy

## Reporting a vulnerability

Please report vulnerabilities privately via GitHub's security advisories:
the repository's **Security** tab → **Report a vulnerability**
(https://github.com/larnsce/llm-wiki/security/advisories/new).
Do not open a public issue for anything that could expose a user's
credentials or personal data before a fix exists.

Ordinary bugs — including false negatives in the credential lint that you
can demonstrate with **fake** example tokens — are fine as regular
[GitHub issues](https://github.com/larnsce/llm-wiki/issues).

## Supported versions

The latest release (and the `main` branch) is supported. There are no
backports to older versions.

## What counts as a vulnerability here

llm-wiki is a local-first tool: there is no server, no network service, and
no account system. The security surface that matters is **data leaving the
machine through git**:

- a way for credentials or secrets to reach git-tracked files that the
  lint's credential scan (rule 6) does not catch;
- a way for content of a `sensitive_source_types` source to end up outside
  its gitignored `ingested/<type>/` path (ingest REQ-046);
- a workflow that writes personal data somewhere the documentation says it
  never goes (e.g. anything crossing the L1/L2 boundary described in
  `docs/faq.md`).

If you find one of these, that is exactly what the private report path
above is for.
