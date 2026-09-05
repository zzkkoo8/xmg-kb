# ADR-0002：默认开源组件基线

**Status:** Accepted

## Context

项目要求自托管、成熟组件优先、人类可编辑、AI 可读写、高质量 RAG、易打包和分发。

## Decision

默认主链：

```text
BookStack
Prefect
Docling Serve
MinerU fallback
RAGFlow
Langfuse
Simple Curator
KAG/OpenSPG POC
```

AI Wiki 标准接口：

```text
BookStack REST API
+
thin xmgkb-mcp adapter
```

## Why BookStack

- MIT；
- 自托管；
- WYSIWYG + Markdown；
- REST API；
- 权限；
- History；
- Attachment；
- Webhook；
- Import/Export。

## Alternatives

### Outline

优点：

- UX 强；
- 第一方 API/MCP 强。

未默认选择：

- 当前 BSL 1.1 不是 Open Source License。

### Docmost

优点：

- 现代协作 UI；
- 开源 Core。

未默认选择：

- AI 稳定读写所需公开 API 能力仍需针对当前稳定版重新验证。

## Consequences

- 公共架构满足“开源优先”；
- 需要维护一个很薄的 MCP Adapter；
- 上游组件保持独立升级，不 fork。

## Validation

在 Human Wiki POC 阶段验证：

- 编辑体验；
- REST API；
- 权限；
- History；
- Backup/Restore；
- AI Review Workflow。

若失败，需要新 ADR 才能替换默认 Wiki。
