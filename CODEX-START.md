# Codex 开局指令

你现在接手 xmg-kb。

本轮不要先写代码。先重新建立当前 Feature 的可信状态，然后只推进一个 Phase Gate。

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
10. 当前 Feature 相关 ADR

然后检查：

```bash
git status
git branch --show-current
git log --oneline --decorate -20
```

## 2. 先判断当前 Gate

按照 `docs/roadmap.md` 从前往后检查。

选择：

> 最靠前的、前置条件已满足但尚未 PASS 的 Phase。

在修改任何代码前先输出：

```text
CURRENT_PHASE:
CURRENT_GATE:
CURRENT_STATUS:
PREREQUISITES:
BLOCKERS:
THIS_RUN_GOAL:
```

## 3. 一次只推进一个 Gate

本轮目标是：

```text
当前 Gate
→ 设计
→ 实现
→ 测试
→ 验收
→ PASS / BLOCKED
```

达到 PASS 后停止，不顺便推进下一 Phase。

## 4. 不重复造轮子

优先检查当前实现：

```bash
find .
rg -n "<相关关键词>"
git log -- <相关路径>
```

发现已有 Adapter / Flow / Policy / Test：

优先复用、补齐、修复和验证。

禁止创建平行第二套实现。

## 5. 架构不可突破

生产主链保持：

```text
Evidence
→ Prefect
→ Docling Serve / MinerU
→ Document Governance
→ Knowledge Engineering
→ BookStack Review
→ BookStack Canonical
→ RAGFlow Parser / Chunker / Indexer
→ Hybrid Retrieval / Rerank
→ AI QA
→ Langfuse
→ Knowledge Evolution
```

## 6. 数据与公共仓库安全

本仓库是公开代码库。

任何真实运行数据都必须在仓库外。

不得提交：

- 私有技术文档；
- PDF/Office 源文件；
- 真实 parsed/normalized 数据；
- 数据库；
- RAG 索引；
- Trace/日志；
- 内部报告；
- 真实部署路径/内部地址；
- Secrets。

所有测试数据必须是 synthetic/public fixture。

提交前严格执行 `docs/publication-policy.md`。

## 7. 代码范围

只开发必要的：

- Adapter
- Policy
- Schema
- Prompt
- Flow
- Mapping
- Sync
- MCP safety layer
- Tests

不要 fork 或重写成熟上游组件。

## 8. 验收

当前 Phase 的每条 Acceptance 建表：

| Acceptance | Result | Evidence |
|---|---|---|

强制项全部 PASS 才能标记 Phase PASS。

## 9. 最终回复

只输出：

1. Current Gate
2. Starting State
3. Changes
4. Tests
5. Acceptance
6. Git commit
7. Result: PASS/BLOCKED
8. Next Gate

不要粘贴大量日志。
