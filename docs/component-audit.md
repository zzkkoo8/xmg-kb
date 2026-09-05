# Component Audit

This document records the current architecture decision criteria for xmg-kb.

## Decision criteria

Components are evaluated in this order:

1. self-hostable;
2. mature and actively maintained;
3. open-source licensing preferred;
4. stable documented API;
5. practical production operations;
6. easy packaging and upgrade path;
7. ability to preserve provenance and data portability;
8. minimal custom code.

## Human wiki

### Selected: BookStack

Rationale:

- MIT licensed;
- self-hosted and lightweight;
- active 2026 release cycle;
- WYSIWYG and Markdown editors;
- books/chapters/pages hierarchy;
- attachments, page history, permissions, comments, tags and templates;
- built-in REST API for external read/write automation;
- webhooks and documented backup/maintenance model.

AI read/write is implemented through the supported REST API. A thin MCP adapter can provide a standard agent interface without coupling agents to the wiki database.

### Not selected as default: Outline

Outline provides excellent UX and first-party API/MCP integration, but its current Business Source License 1.1 explicitly states that it is not an open-source license. It can remain an optional deployment profile where source-available licensing is acceptable.

### Not selected as default: Docmost

Docmost Core is AGPL-3.0 and has a modern collaborative UI, but its official REST API currently requires the Enterprise edition. Depending on private/internal API routes would weaken upgrade stability for the AI-edit requirement.

### Alternative: Wiki.js

Wiki.js remains a valid AGPL-3.0 alternative with a GraphQL API and Markdown focus. BookStack is preferred for the current baseline because of its simple deployment, MIT license, mature REST API and active operational documentation.

## Orchestration

### Selected: Prefect

Prefect provides Python-native flows, task retries, caching, scheduling, event triggers, concurrency control and a self-hosted server. These are infrastructure concerns that should not be reimplemented in xmg-kb.

## Document parsing

### Selected primary: Docling Serve

Docling is MIT licensed and production-oriented. Docling Serve exposes asynchronous conversion endpoints with task IDs and status polling, making it suitable for durable batch orchestration.

### Selected fallback: MinerU

MinerU handles complex PDFs, OCR, formulas and tables well and supports several mainstream office/document formats. Its current license is based on Apache-2.0 with additional terms, so deployments should review those terms before redistribution or commercial service exposure.

## Production RAG

### Selected: RAGFlow

RAGFlow owns production parsing/chunking/indexing/retrieval for canonical wiki content. xmg-kb does not implement a second vector database or chunk engine.

The production index should contain canonical wiki content only. Raw evidence and review content may use separate administrator-only staging datasets.

## Observability and evaluation

### Selected: Langfuse

Langfuse core capabilities are MIT licensed and self-hostable. It provides tracing, feedback, datasets, experiments and evaluation, avoiding the need for a custom AI observability platform.

## Knowledge engineering

### Optional POC: OpenSPG/KAG

OpenSPG is Apache-2.0. KAG is tested only as a knowledge-engineering accelerator. The baseline pipeline must remain functional without it.

Adoption requires a controlled benchmark showing meaningful improvement in knowledge-unit extraction, alignment, conflict detection or canonical synthesis.

## Packaging decision

xmg-kb should distribute a **thin orchestration layer**, not forks of upstream products.

Preferred delivery model:

- pinned upstream container images;
- component-specific Compose/deployment files;
- a project-level Makefile or CLI for lifecycle commands;
- Python glue packaged with `uv`/standard Python packaging;
- synthetic fixtures only;
- environment templates with placeholders;
- automated public-repository safety checks.

Avoid one huge custom Compose file that rewrites every upstream deployment unless a later release benchmark proves that consolidation is worth the maintenance cost.
