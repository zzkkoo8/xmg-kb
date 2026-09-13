# AGENTS.md

本文件是 xmg-kb 仓库内 AI Agent / Codex 的最高项目级协作约束。

## 1. 项目定位

xmg-kb 是独立知识库基础设施，只负责：

- Ingestion；
- Document Governance；
- Knowledge Governance；
- Canonical Wiki；
- RAG；
- Knowledge/Retrieval API；
- MCP；
- Knowledge Operations / Backup / Observability。

不负责业务 Agent、聊天机器人、工单、钉钉、自动运维和 Multi-Agent Runtime。任何外部项目都只能作为消费者，不得成为 xmg-kb Phase Gate。

## 2. 开始任何任务前

必须按顺序阅读：

1. `README.md`
2. `CODEX-START.md`
3. `docs/requirements.md`
4. `docs/architecture.md`
5. `docs/roadmap.md`
6. `docs/component-audit.md`
7. `docs/development.md`
8. `docs/testing.md`
9. `docs/publication-policy.md`
10. 与当前任务直接相关的 ADR

不要根据聊天历史猜项目状态，以本地代码、运行状态、测试和最新报告为证据。

## 3. 分支治理

- `main` 保存稳定公开基线；
- Feature 使用独立分支；
- 不覆盖其他 Agent 未提交工作；
- 修改前检查 `git status`、当前 branch 和最近 commit。

## 4. Phase Gate

`docs/roadmap.md` 是阶段门禁基线。

只能推进：

> 最靠前的、Prerequisites 已满足但尚未 PASS 的 Phase。

状态只允许：

- `NOT_STARTED`
- `IN_PROGRESS`
- `IMPLEMENTED_UNVERIFIED`
- `PASS`
- `BLOCKED`
- `DEVIATED`

已有后续资产允许标记为 `PRE_EXISTING_REUSABLE_ASSET`，优先复用；`DEVIATED` 不等于推倒重做。

`PASS` 必须有命令、测试、API、运行状态或数据指标等新鲜证据。

## 5. 默认主链

- BookStack
- Prefect
- Docling Serve
- MinerU fallback
- LibreOffice
- ClamAV
- RAGFlow
- Langfuse
- Simple Curator
- KAG/OpenSPG POC（可选）

核心自研范围：

- Adapter
- Schema
- Policy
- Prompt
- Prefect Flow
- Mapping / Provenance
- Wiki/RAG Sync
- Knowledge / Retrieval API
- MCP Safety Layer
- Acceptance Tests

禁止无充分证据自研 Wiki、OCR/PDF Layout、Workflow Runtime、Vector DB、Chunk Engine、Search Engine、Trace/Eval Platform 或通用 MCP Runtime。

## 6. Source of Truth

```text
Evidence
→ Governance
→ Review
→ BookStack Canonical Wiki
→ RAGFlow Derived Index
→ API / MCP
```

BookStack Canonical 是人类可维护的权威知识层；RAGFlow 是可重建派生索引。

禁止：

- Raw / Legacy / Review → Production RAG；
- RAG Chunk 反向覆盖 Canonical；
- 两套 Canonical Master 并行维护。

## 7. Knowledge Unit != RAG Chunk

```text
Knowledge Unit = 治理单位
RAG Chunk      = 检索单位
```

不得混用。

## 8. Adapter / Harness 原则

核心逻辑依赖稳定接口，而不是具体组件内部实现：

```text
SourceAdapter
ParserAdapter
WikiAdapter
RagAdapter
ObservabilityAdapter
```

新增/替换能力优先通过 Adapter / Registry 完成。

## 9. AI 知识权限

默认允许：Search、Read、Source Lookup、Create Review、Patch Review、Comment、RAG Search/Context。

默认禁止：Delete Canonical、绕过 Review、静默改写关键技术参数、静默解决版本/冲突、直接操作 Wiki 数据库。

## 10. 数据与公共仓库边界

公共 Git 只保存代码和公开设计。

禁止提交真实知识库内容、生产数据、数据库、索引、日志、Trace、内部报告、真实路径、内部 URL、Secrets。

示例统一使用：

```text
/srv/xmg-kb
https://wiki.example.invalid
https://rag.example.invalid
```

详见 `docs/publication-policy.md`。

## 11. 测试与完成声明

新功能至少具备 Unit Test；关键 Adapter 具备 Integration Test；关键路径具备 Smoke/E2E Test。

禁止用“应该完成”“理论可用”代替验收。如果无法验证，状态必须是 `IMPLEMENTED_UNVERIFIED` 或 `BLOCKED`。

提交前执行当前范围测试、`git diff --check`、`git status --short` 和公共仓库安全检查。