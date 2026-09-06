# ADR-0002：默认自托管组件基线

**Status:** Accepted

## Context

项目要求自托管、成熟组件优先、人类可编辑、AI 可读写、高质量 RAG、易打包和分发。

## Decision

默认主链：

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

AI Wiki 标准接口：

```text
Outline API/MCP
+
Webhook / State adapter
```

## Why Outline

- 自托管；
- 协作编辑体验；
- Collections / Nested Documents；
- API / MCP；
- 权限；
- History；
- Attachment；
- Webhook；
- Import/Export。

## Alternatives

### BookStack

优点：

- MIT；
- 运维成熟；
- REST API。

未默认选择：

- 与 v7 已选定的 Outline Collection、API/MCP、Webhook 和 Mapping 合同不一致；
- 未完成替换所需的迁移与验收。

### Docmost

优点：

- 现代协作 UI；
- 开源 Core。

未默认选择：

- AI 稳定读写所需公开 API 能力仍需针对当前稳定版重新验证。

## Consequences

- Outline 是明确记录的 source-available 许可证例外；
- 需要维护很薄的 Webhook / State Adapter；
- 上游组件保持独立升级，不 fork。

## Validation

在 Human Wiki POC 阶段验证：

- 编辑体验；
- API / MCP；
- 权限；
- History；
- Backup/Restore；
- AI Review Workflow。

若失败，需要新 ADR 才能替换默认 Wiki。
