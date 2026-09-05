# Execution Roadmap

This roadmap is intentionally phase-gated. A later phase must not be enabled until its prerequisite evidence is verified.

## Phase 0 — Preflight

Goal: verify host capacity, storage, container runtime, network access and component compatibility.

Acceptance:

- host resource report exists;
- storage headroom is measured;
- ports and persistent paths are allocated;
- deployment mode is selected (`all-on` or staged runtime);
- no knowledge data has been modified.

## Phase 1 — Bootstrap all components

Install, pin and smoke-test the selected components without ingesting production knowledge.

Acceptance for each component:

- exact version and image digest recorded;
- service starts;
- API/UI health check succeeds;
- restart preserves state where applicable;
- default credentials are removed or disabled;
- no production dataset has been loaded.

## Phase 2 — Source registry and manifest

Build an immutable inventory of source materials and previously curated knowledge.

Acceptance:

- every eligible source has a stable source ID;
- hashes and metadata are stored;
- source provenance is queryable;
- inventory can be rerun incrementally;
- no source file is modified.

## Phase 3 — Reuse mapping

Prefer previously curated material over reparsing equivalent raw source files.

Final states include:

- accepted reuse;
- needs repair;
- confirmed duplicate;
- archive-only;
- unsupported;
- quarantined;
- unmapped.

Acceptance:

- mapping rules are deterministic and documented;
- accepted reusable documents are not sent back through expensive parsing;
- unresolved mappings are visible.

## Phase 4 — Parser pilot

Run a representative corpus through Docling Serve with MinerU fallback.

Acceptance:

- asynchronous submit/status/result flow works;
- retries and resumability work;
- failures are isolated per document;
- structured output and provenance are persisted;
- critical facts in high-value samples are preserved;
- parser routing thresholds are calibrated from evidence.

## Phase 5 — Bulk ingestion runtime

Scale the parser workflow with bounded batches and explicit concurrency limits.

Acceptance:

- at least 1,000 representative files can be queued safely;
- worker restart does not lose task state;
- completed documents are not duplicated;
- storage growth and processing throughput are measured;
- failure rates remain within the pilot threshold.

## Phase 6 — Document governance

Apply exact deduplication, near-document relations, taxonomy, version scope, authority and security classification.

Acceptance:

- exact duplicate precision is 100%;
- near-duplicate precision is at least 95% on the reviewed sample;
- critical version merges have zero known errors;
- required metadata coverage is at least 99%;
- unknown metadata is explicitly marked rather than invented.

## Phase 7 — Human wiki pilot

Validate BookStack as the human knowledge workspace before large-scale canonicalization.

Acceptance:

- WYSIWYG and Markdown editing are acceptable;
- pages, chapters/books, attachments, history, comments, permissions and search work;
- REST API can safely read and write review content;
- backup/restore is tested;
- human owner explicitly approves daily use.

## Phase 8 — Knowledge-engineering pilot

Compare a simple curator baseline against KAG/OpenSPG on the same real corpus.

Acceptance targets:

- source traceability: 100%;
- knowledge-unit factual precision: at least 98%;
- critical wrong merges: 0;
- reviewed alignment precision: at least 95%;
- at least 30 canonical drafts are produced and human-reviewed.

KAG is adopted only if it provides meaningful quality improvement at acceptable operational cost.

## Phase 9 — Canonical knowledge workflow

Create review pages and promote approved knowledge to canonical wiki locations.

Acceptance:

- every canonical page has traceable sources;
- version scope is explicit;
- unsupported claims are absent;
- obvious duplicate canonical pages are absent;
- review-to-canonical permissions are enforced.

## Phase 10 — RAG production ingestion

Synchronize canonical wiki pages into RAGFlow.

Production ingestion:

```text
Canonical page
  -> Parser
  -> Chunker
  -> optional Transformer
  -> Indexer
```

Acceptance:

- production contains canonical content only;
- review/raw/archive content cannot be retrieved;
- every chunk inherits stable page/revision metadata;
- incremental update is idempotent;
- a failed new revision leaves the old active revision available.

## Phase 11 — Retrieval benchmark

Build a gold QA set and compare retrieval configurations.

At minimum compare:

- vector only;
- full-text only;
- hybrid;
- hybrid + reranking;
- multiple chunk-size/structure strategies.

Initial targets:

- Top-5 recall >= 95%;
- critical Top-5 recall >= 98%;
- citation correctness >= 95%;
- correct refusal >= 98%;
- critical hallucination = 0.

## Phase 12 — AI knowledge-management interface

Expose safe wiki operations to AI through BookStack REST API and a thin MCP adapter.

Allowed by default:

- search;
- read;
- create review draft;
- patch review draft;
- comment;
- source lookup.

Disallowed by default:

- delete canonical page;
- bypass review;
- overwrite version/conflict decisions silently.

## Phase 13 — Observability and evaluation

Connect QA traces to Langfuse.

Acceptance:

- query, retrieved canonical IDs, answer, citations, latency and feedback are recorded;
- evaluation datasets can be created;
- failed or weak retrieval cases are queryable.

## Phase 14 — Knowledge evolution

Classify usage signals into:

- `GOOD`
- `WEAK`
- `MISSING`
- `CONFLICT`
- `OUTDATED`
- `FRAGMENTED`

High-priority events produce review proposals, never direct canonical writes.

## Phase 15 — Scale validation

Run the complete flow on multiple domains with different data quality.

Acceptance:

- the same codebase is reused;
- differences are primarily taxonomy, aliases, policy configuration and prompts;
- domain expansion does not require a parallel pipeline implementation.

## Phase 16 — Full migration

Migrate source materials by domain/product in bounded waves.

Acceptance:

- every source has a final state;
- unresolved sources are zero before retirement of any legacy store;
- canonical source traceability is 100%;
- production RAG remains canonical-only;
- migration and restore reports pass.

## Phase 17 — Operations and distribution

Finalize reproducible packaging, health checks, backup/restore, upgrade procedure and release artifacts.

A release is ready only when a clean host can deploy from public code/config templates without any private source material.
