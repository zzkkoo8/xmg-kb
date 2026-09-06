# AGENTS.md

本文件是 xmg-kb 仓库内 AI Agent / Codex 的最高项目级协作约束。

## 1. 开始任何任务前

必须按顺序阅读：

1. `README.md`
2. `CODEX-START.md`
3. `docs/requirements.md`
4. `docs/architecture.md`
5. `docs/roadmap.md`
6. `docs/development.md`
7. `docs/testing.md`
8. `docs/publication-policy.md`
9. 与当前任务直接相关的 ADR

不要根据聊天历史猜项目状态。

## 2. 分支治理

- `main` 只保存已经审阅、可回退的稳定基线。
- 每个 Feature 使用独立分支。
- 禁止直接在 `main` 开发。
- 推荐命名：`feature/<slug>`、`fix/<slug>`、`docs/<slug>`。
- 一个 Feature 的设计、实现、测试和文档应尽量绑定在同一分支/PR。
- 不覆盖其他 Agent 未提交或不属于当前任务的工作。

## 3. 研发流程

复杂任务遵循：

```text
Inspect
→ Requirements
→ Design
→ Plan
→ Tests
→ Implementation
→ Verification
→ Report
→ Commit / PR
```

禁止先大规模实现、最后统一补测试。

## 4. Phase Gate

`docs/roadmap.md` 是阶段门禁基线。

只能推进：

> 最靠前的、其 Prerequisites 已满足但尚未 PASS 的 Phase。

不得因为后续目录、代码或容器已经存在就跳过前置 Gate。

状态只允许：

- `NOT_STARTED`
- `IN_PROGRESS`
- `IMPLEMENTED_UNVERIFIED`
- `PASS`
- `BLOCKED`
- `DEVIATED`

`PASS` 必须有命令、测试、API、运行状态或数据指标等可验证证据。

## 5. 成熟组件优先

默认主链：

- Outline
- Prefect
- Docling Serve
- MinerU fallback
- RAGFlow
- Langfuse
- Simple Curator
- KAG/OpenSPG POC

禁止无充分证据自研：

- Wiki / Rich Editor
- PDF/OCR/Layout Engine
- Workflow Runtime
- Vector DB
- Chunk Engine
- Search Engine
- Trace/Eval Platform
- 通用 MCP 协议框架

自研范围应集中在：

- Adapter
- Schema
- Policy
- Prompt
- Prefect Flow
- Mapping / Provenance
- Wiki/RAG Sync
- 安全 MCP Tools
- Acceptance Tests

## 6. 数据边界

公共 Git 仓库永远只保存代码和公开设计。

任何真实知识库内容、生产数据、数据库、日志、Trace、内部报告、真实路径、内部 URL、密钥均不得提交。

所有示例路径使用：

```text
/srv/xmg-kb
/srv/xmg-kb/evidence
```

所有示例 URL 使用：

```text
https://wiki.example.invalid
https://rag.example.invalid
```

详见 `docs/publication-policy.md`。

## 7. Source of Truth

架构层面：

```text
Evidence
→ Governance
→ Review
→ Canonical Wiki
→ Derived RAG Index
```

Outline Canonical Collections 是人类可维护的权威知识层。

RAGFlow 是派生索引，不是事实源。

禁止：

- Raw → Production RAG
- Review → Production RAG
- RAG Chunk 反向覆盖 Canonical
- 两套 Canonical Master 并行维护

## 8. Knowledge Unit != RAG Chunk

永远区分：

```text
Knowledge Unit
= 治理单位
= 去重 / 版本 / 冲突 / Canonical

RAG Chunk
= 检索单位
= Retrieval Context
```

## 9. AI Wiki 权限

AI 默认允许：

- Search
- Read
- Create Review
- Patch Review
- Comment
- Source Lookup

AI 默认禁止：

- Delete Canonical
- 绕过 Review
- 静默改写关键技术参数
- 静默解决版本/冲突

## 10. 测试

新功能至少具备：

- Unit Test；
- 关键 Adapter 的 Integration Test；
- 关键端到端路径的 Smoke/E2E Test。

所有测试只使用合成数据或公开 fixture。

不得为了测试拉入真实内部文档。

## 11. Git 提交

- 每个可独立验收的变更使用语义清晰 Commit。
- 提交前执行 `git diff --check`。
- 检查 `git status --short`。
- 运行当前范围测试。
- 运行公共仓库安全检查。
- 禁止提交 `.env`、数据库、运行数据、二进制私有文档。

## 12. 完成声明

禁止使用：

- “应该完成”
- “理论可用”
- “大概率正常”

只能依据证据报告：

- `PASS`
- `BLOCKED`

如果无法验证，状态是：

`IMPLEMENTED_UNVERIFIED`。
