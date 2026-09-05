# Architecture

## 1. System objective

xmg-kb is a self-hosted knowledge engineering platform that converts heterogeneous technical documents into two products:

1. a human-maintainable canonical wiki;
2. a high-quality RAG index for AI assistants.

The system deliberately separates **evidence**, **canonical knowledge**, and **retrieval chunks**.

## 2. Reference architecture

```text
Evidence Sources
  |-- Markdown / HTML
  |-- PDF / images
  |-- DOCX / PPTX / XLSX
  |-- historical curated knowledge
  |
  v
Source Registry + Manifest
  |
  v
Prefect
  |-- retry / cache / resume / scheduling / concurrency
  |
  v
Document Parsing
  |-- Docling Serve (primary)
  `-- MinerU (complex-document fallback)
  |
  v
Normalized Evidence
  |-- structured JSON
  |-- Markdown
  |-- assets
  `-- provenance metadata
  |
  v
Document Governance
  |-- exact deduplication
  |-- near-document deduplication
  |-- metadata and taxonomy
  |-- version scope
  |-- authority
  `-- security classification
  |
  v
Knowledge Governance
  |-- sections
  |-- knowledge units
  |-- duplicate/supplement/supersede relations
  |-- conflicts
  `-- canonicalization policy
  |
  v
BookStack Review Area
  |
  v
BookStack Canonical Wiki
  |
  +------------------------------+
  |                              |
  | Full-document API            | Canonical-only sync
  v                              v
Knowledge-management AI       RAGFlow
                              |-- Parser
                              |-- Chunker
                              |-- optional Transformer
                              `-- Indexer
                                   |
                                   v
                         Hybrid Retrieval + Reranker
                                   |
                                   v
                                  QA AI
                                   |
                                   v
                                Langfuse
                                   |
                                   v
                      Knowledge Evolution Candidates
                                   |
                                   `----> Review Area
```

## 3. Component selection

### BookStack — canonical human wiki

BookStack is the default human knowledge layer because it is MIT licensed, self-hosted, actively maintained, lightweight, and provides both WYSIWYG and Markdown editing together with page history, attachments, permissions, webhooks and a built-in REST API.

The wiki is the **authoritative human knowledge store**. AI must not edit its database directly. All automated operations use the supported REST API.

A thin xmg-kb MCP gateway may expose safe AI operations such as search, read, create-review, patch-review and comment. Destructive canonical operations should be disabled by default.

### Prefect — orchestration

Prefect owns durable workflow state: scheduling, retries, caching, concurrency, resumability and event-driven execution. xmg-kb does not implement another workflow engine.

### Docling Serve — primary parser

Docling Serve provides an asynchronous API for document conversion. Parsed output should preserve structured representation and Markdown where possible.

### MinerU — fallback parser

MinerU is used only for inputs where Docling quality fails acceptance checks, particularly complex layouts, scanned PDFs, OCR-heavy documents, formulas or difficult tables.

### RAGFlow — retrieval layer

RAGFlow indexes **canonical wiki content only** for production QA. Raw and review content may be placed in separate staging datasets for administrator research but must never leak into production retrieval.

Production ingestion is:

```text
Canonical Wiki
  -> Parser
  -> Chunker
  -> optional Transformer
  -> Indexer
  -> metadata filtering
  -> hybrid retrieval
  -> reranking
```

### Langfuse — trace and evaluation

Langfuse records query/retrieval/answer traces, user feedback and evaluation results. These signals feed the knowledge-evolution queue but never directly overwrite canonical knowledge.

### OpenSPG/KAG — optional POC

KAG/OpenSPG is evaluated against a simpler curator baseline on real data. It is adopted only if it materially improves knowledge-unit quality, alignment, conflict discovery or canonical synthesis without unacceptable operational cost.

## 4. Knowledge layers

### Raw evidence

Immutable source materials. Raw evidence is never the production RAG source.

### Normalized evidence

Machine-generated structured representations. This layer is rebuildable and is not edited by humans as authoritative knowledge.

### Knowledge units

Semantic governance units used for consolidation, versioning and conflict detection. A knowledge unit is not a RAG chunk.

### Canonical articles

Human-readable, reviewable, editable pages in BookStack. These are the authoritative knowledge artifacts.

### RAG chunks

Retrieval units generated from canonical articles. They are derived data and can always be rebuilt.

## 5. Canonicalization actions

The canonicalization policy may emit only:

- `CREATE`
- `PATCH`
- `SUPPLEMENT`
- `SUPERSEDE`
- `CONFLICT_REVIEW`
- `NO_ACTION`

It must never perform an unreviewed automatic delete of canonical knowledge.

## 6. Indexing strategy

Production retrieval uses:

- canonical-only input;
- heading-aware chunking;
- code/table/procedure boundary protection;
- inherited metadata on every chunk;
- hybrid full-text + vector retrieval;
- reranking;
- incremental sync by stable source ID, revision and content hash;
- atomic activation of new revisions;
- traceability from every retrieved chunk back to its wiki page and revision.

Chunk size and retrieval settings are selected by benchmark, not by fixed assumptions.

## 7. Packaging strategy

The project should be easy to develop, install and distribute without creating one fragile monolithic Compose file.

Recommended repository layout:

```text
deploy/
  bookstack/
  prefect/
  docling-serve/
  mineru/
  ragflow/
  langfuse/
  kag-poc/

src/xmg_kb/
  adapters/
  flows/
  policies/
  schemas/
  mcp/

config/
  examples/

scripts/
  bootstrap
  verify
  backup

tests/
```

Use upstream-supported deployment artifacts whenever practical. xmg-kb should provide thin wrappers such as:

```text
make bootstrap
make up-core
make up-ingestion
make up-rag
make up-observability
make verify
make test
make backup
```

The wrappers orchestrate pinned upstream components; they do not reimplement those components.

## 8. Data-flow activation

All components may be installed and smoke-tested early, but production data flows are enabled only after their prerequisites pass.

```text
Bootstrap components
  -> source inventory
  -> reuse mapping
  -> parser pilot
  -> document governance
  -> knowledge engineering pilot
  -> canonical wiki pilot
  -> RAG benchmark
  -> QA integration
  -> observability
  -> knowledge evolution
  -> full-scale migration
```

## 9. Non-goals

xmg-kb does not build its own:

- wiki editor;
- OCR engine;
- PDF layout engine;
- workflow runtime;
- vector database;
- search engine;
- tracing platform;
- evaluation dashboard;
- generic graph database;
- MCP protocol implementation.

Only domain-specific glue, policy and adapters are custom code.
