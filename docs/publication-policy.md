# Public Repository Publication Policy

This repository is public. It is intended for architecture, source code, tests, deployment templates and public documentation only.

## Allowed

- architecture and design documents written with generic examples;
- source code;
- unit/integration tests using synthetic fixtures;
- Docker/Compose/Helm/Make/Task configuration templates;
- `.env.example` files containing placeholders only;
- public component version/license manifests;
- generic operational runbooks;
- generated diagrams that contain no private topology or data;
- benchmark methodology and synthetic benchmark data.

## Forbidden

Never commit or upload:

- source knowledge-base documents;
- vendor/customer/internal manuals collected for private use;
- parsed or normalized corpora;
- production wiki exports;
- production RAG chunks or vector indexes;
- database dumps;
- runtime state databases;
- logs or trace exports from real users;
- internal audit reports containing private data;
- credentials, tokens, cookies, API keys, private certificates or `.env` files;
- internal hostnames, private IP addresses or internal service URLs;
- private filesystem paths from a real deployment;
- customer/vendor-specific confidential data;
- screenshots from internal systems;
- backups, archives or binary document bundles.

## Repository examples must use neutral placeholders

Use:

```text
/srv/xmg-kb
/srv/xmg-kb/evidence
https://wiki.example.invalid
https://rag.example.invalid
10.0.0.0/24 only when explicitly marked as documentation-reserved example data
```

Do not copy real deployment paths, hostnames, addresses or user data from a working system.

## Data separation

Public code must assume runtime data lives outside the Git repository:

```text
Repository checkout
  -> code/config/templates only

External runtime root
  -> evidence
  -> parsed/normalized data
  -> databases
  -> indexes
  -> logs
  -> backups
```

No program should require private knowledge files to exist inside the repository checkout.

## Mandatory pre-push checks

Before any public push:

1. run tests;
2. run `git diff --check`;
3. run a secret scanner such as Gitleaks;
4. scan for forbidden runtime paths/hostnames;
5. inspect all new binary files;
6. inspect `git status --short` manually;
7. confirm no generated knowledge artifacts are staged.

The repository should provide `scripts/check-public.sh` to automate these checks.

## Default-deny binary policy

Technical source documents are not release artifacts. The default `.gitignore` should reject common private document/archive/database formats. Public documentation diagrams should use reviewed text-based formats such as SVG or Mermaid whenever possible.

## Release rule

A release artifact may contain:

- application code;
- public deployment manifests;
- migration/schema code;
- synthetic fixtures;
- templates;
- public docs.

A release artifact must never contain runtime evidence or production knowledge.
