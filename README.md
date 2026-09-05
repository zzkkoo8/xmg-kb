# xmg-kb

Open-source knowledge-base engineering stack for turning heterogeneous technical documents into a human-maintainable wiki and a high-quality RAG knowledge source.

## Goals

- Human-readable and human-editable technical wiki
- AI-readable and controlled AI-editable knowledge through APIs/MCP
- Resumable high-volume document ingestion and normalization
- Deduplication, provenance, version and conflict governance
- Canonical knowledge separated from raw evidence
- Incremental RAG chunking, hybrid retrieval, reranking and citation
- Reproducible packaging and self-hosted deployment

## Reference architecture

```text
Evidence Sources
      |
      v
Prefect Orchestration
      |
      v
Docling Serve ----> MinerU fallback
      |
      v
Normalize / Deduplicate / Version / Provenance
      |
      v
Knowledge Governance / Canonicalization
      |
      v
BookStack Review -> Canonical Wiki
      |
      v
RAGFlow Parser -> Chunker -> Indexer
      |
      v
Hybrid Retrieval -> Reranker -> AI QA
      |
      v
Langfuse Feedback / Evaluation
```

KAG/OpenSPG is evaluated as an optional knowledge-engineering accelerator and is not a mandatory runtime dependency.

## Public repository policy

This repository contains **software and public design material only**. It must never contain private knowledge-base content, source documents, customer/vendor documents, internal reports, credentials, private host paths, internal IP addresses, database dumps, parsed corpora, vector indexes, backups, logs or runtime state.

See `docs/publication-policy.md` once the architecture baseline is added.

## License

Project license will be selected before the first software release. Third-party components retain their own licenses.
