# Codex 开局指令

你现在接手 xmg-kb。

xmg-kb 是独立知识库基础设施，只负责 Ingestion、Governance、Canonical Wiki、RAG、API、MCP 和知识库运维能力。不要进入或修改任何外部业务 Agent 项目，也不要把外部 Agent 状态当作 xmg-kb Gate。

## 1. 阅读顺序

完整阅读：

1. `AGENTS.md`
2. `docs/requirements.md`
3. `docs/architecture.md`
4. `docs/roadmap.md`
5. `docs/component-audit.md`
6. `docs/design-audit.md`
7. `docs/development.md`
8. `docs/testing.md`
9. `docs/publication-policy.md`
10. 当前任务相关 ADR

然后检查：

```bash
git status
git branch --show-current
git log --oneline --decorate -20
```

以本地代码、服务、测试和最新 reports 为事实依据，不根据聊天历史猜当前状态。

## 2. 确定 Current Gate

按照 `docs/roadmap.md` 从前往后，找到最靠前的、前置条件已满足但尚未 PASS 的 Phase。

修改代码前输出：

```text
CURRENT_PHASE:
CURRENT_GATE:
CURRENT_STATUS:
PREREQUISITES:
BLOCKERS:
THIS_RUN_GOAL:
```

一次只推进一个 Gate。达到 `PASS` 或 `BLOCKED` 后停止，不顺便推进后续 Phase。

## 3. 当前架构边界

```text
Evidence
→ Prefect Ingestion
→ Docling Serve / MinerU
→ Document Governance
→ Knowledge Governance
→ BookStack Review
→ BookStack Canonical
→ RAGFlow
→ Knowledge / Retrieval API
→ MCP
→ External Consumers
```

Langfuse 是 Observability/Evaluation；KAG/OpenSPG 是 Optional POC。

外部消费者不属于 xmg-kb：不要实现聊天机器人、工单、钉钉、Multi-Agent、业务 Agent Runtime。

## 4. 不重复造轮子

修改前先使用 `find`、`rg`、`git log -- <path>` 检查现有 Adapter / Flow / Policy / Test / Deploy。

已有能力优先复用、修复、补测试和验证；禁止创建平行第二套 Parser、Flow、State、Wiki/RAG Adapter。

## 5. 历史资产处理

提前存在的 Manifest、Mapping、Parsed、Provenance 等资产，不因当前 Phase 尚未通过而删除或重做。

统一按 `PRE_EXISTING_REUSABLE_ASSET` 处理，后续 Gate 逐项重新验收。

遵循：

```text
Legacy First
Raw Fallback
```

## 6. 数据与公共仓库安全

真实运行数据必须在 Git checkout 外。

不得提交私有技术文档、真实 parsed/normalized/knowledge 数据、数据库、RAG Index、Trace/日志、内部报告、真实部署路径/地址或 Secret。

测试只使用 synthetic/public fixture。

## 7. 自研范围

只开发必要的：

- Adapter
- Policy
- Schema
- Prompt
- Prefect Flow
- Mapping / Provenance
- Wiki/RAG Sync
- Knowledge / Retrieval API
- MCP Safety Layer
- Tests

不 fork 或重写成熟上游组件。

## 8. 验收

当前 Phase 每条 Acceptance 建表：

| Acceptance | Result | Evidence |
|---|---|---|

强制项全部有新鲜证据才能标记 `PASS`。

## 9. 最终回复

只汇报：Current Gate、Starting State、Changes、Tests、Acceptance、Git Commit、Result(PASS/BLOCKED)、Next Gate。

不要粘贴大量日志。