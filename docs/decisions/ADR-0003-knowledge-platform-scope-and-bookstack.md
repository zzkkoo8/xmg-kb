# ADR-0003：知识平台边界与 BookStack 默认 Wiki

**Status:** Accepted

## Context

xmg-kb 的目标已从“围绕某个问答 Agent 建设知识库”收敛为独立的 Knowledge Platform / Knowledge Infrastructure。

项目需要稳定覆盖：知识入库、知识治理、Canonical Wiki、RAG、API、MCP 与知识库运维，同时保持开源优先、组件可替换、易部署、易分发和低维护成本。

## Decision

### 1. 项目边界

xmg-kb 只负责：

```text
Ingestion
Document Governance
Knowledge Governance
Canonical Wiki
RAG
Knowledge / Retrieval API
MCP
Operations / Observability / Backup
```

业务 Agent、聊天机器人、工单、IM Bot、自动运维和 Multi-Agent Runtime 不属于 xmg-kb。

外部系统只作为 API/MCP/RAG Consumer，不成为 xmg-kb Phase Gate。

### 2. 默认主链

```text
BookStack
Prefect
Docling Serve
MinerU fallback
LibreOffice
ClamAV
RAGFlow
Langfuse
Simple Curator
KAG/OpenSPG POC (optional)
```

### 3. Human Wiki

BookStack 作为当前默认 Canonical Wiki。

核心代码只依赖 `WikiAdapter`，不直接依赖 BookStack 数据库或内部表结构。

### 4. Interface

xmg-kb 提供稳定的 Knowledge API、Retrieval API 和 MCP。外部消费者不应直接耦合 BookStack/RAGFlow 内部实现。

## Alternatives

### Outline

优点：协作体验、API/MCP、History、Attachment、Permission、Webhook 能力强。

当前不默认采用：项目强调开源优先，且当前没有必须保留的 Outline 生产数据。未来可通过独立 Adapter/ADR 重新引入。

### 自研 Wiki / RAG / Workflow

拒绝。成熟能力由上游项目提供，xmg-kb 只实现领域治理、Adapter、Flow、API、MCP 和测试。

## Consequences

优点：

- 项目边界清晰；
- xmg-kb 与任何具体业务 Agent 解耦；
- BookStack/RAGFlow 等组件可通过 Adapter 替换；
- 公共仓库可独立开发、测试和分发；
- 避免为了一个消费者污染知识平台核心架构。

成本：

- 需要维护薄 WikiAdapter、RagAdapter、API/MCP 层；
- 需要从旧设计中的 Outline 术语迁移到 BookStack/通用 Wiki 合同；
- 当前 Phase 1 和后续 Wiki/RAG Gate 需要按本 ADR 重新验收。

## Validation

至少验证：

- BookStack Human Wiki POC；
- REST API + WikiAdapter；
- Review → Canonical；
- Canonical-only RAGFlow Sync；
- Knowledge/Retrieval API；
- MCP 安全工具；
- Backup/Restore；
- 外部消费者无需修改 xmg-kb 核心即可接入。

## Rollback

如果 BookStack POC 无法满足核心需求，可新增 ADR 选择其他 Wiki，实现新的 `WikiAdapter` 并迁移 Canonical 数据；不得同时长期维护两个 Canonical Master。