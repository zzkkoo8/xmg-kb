# ADR-0002：旧版默认组件基线（Outline）

**Status:** Superseded by ADR-0003

## Context

早期 v7 为 Human Wiki 选择 Outline，主要看重协作体验、API/MCP、History、Attachment、Permission、Webhook 和 Import/Export。

## Historical Decision

当时默认主链：

```text
Outline
Prefect
Docling Serve
MinerU fallback
RAGFlow
Langfuse
Simple Curator
KAG/OpenSPG POC
```

## Why Superseded

当前 xmg-kb 产品边界进一步收敛为独立 Knowledge Platform，并明确“开源优先、稳定 REST API、易自托管、易分发、组件可替换”。

在当前尚未形成必须保留的 Outline 生产知识前，继续把 Outline 作为 Required Component 会增加许可证例外和后续迁移成本。

因此新的组件与项目边界由 ADR-0003 统一替代。

## Historical Value

本 ADR 保留用于解释设计演进，不再作为当前 Codex/Phase Gate 的实现依据。