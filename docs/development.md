# 开发规范

## 1. 工程目标

xmg-kb 自有代码应保持“薄”。

主要模块：

```text
src/xmg_kb/
├── adapters/
├── flows/
├── policies/
├── schemas/
└── mcp/
```

## 2. Python

推荐：

```text
pyproject.toml
uv.lock
src layout
pytest
ruff
mypy/pyright（按项目最终选择）
```

不要维护大量不可复用的独立脚本。

## 3. Adapter

Adapter 只封装上游稳定接口：

- BookStack；
- Prefect；
- Docling Serve；
- MinerU；
- RAGFlow；
- Langfuse；
- KAG。

业务规则不要散落在 Adapter 中。

## 4. Policy

Policy 放领域判断：

- Reuse；
- Parse Quality；
- Metadata；
- Version；
- Authority；
- Canonicalization；
- Publishing；
- Evolution。

Policy 必须可独立测试。

## 5. Flow

Prefect Flow 负责编排：

- Source Inventory；
- Parse；
- Document Governance；
- Knowledge Engineering；
- Wiki Sync；
- RAG Sync；
- QA Regression；
- Evolution；
- Backup Verify。

Flow 不复制业务逻辑，逻辑进入可测试函数/Policy。

## 6. Idempotency

所有有副作用流程必须满足：

```text
same source
same content hash
same policy version
→ no duplicate side effect
```

## 7. Cache

LLM Cache Key 至少考虑：

```text
input_sha256
prompt_version
schema_version
model_id
task_type
```

相同输入不得重复昂贵调用。

## 8. Error Handling

所有失败必须可分类：

- RETRYABLE；
- FINAL；
- QUARANTINED；
- BLOCKED_MANUAL_REVIEW。

禁止用“catch all + continue”隐藏失败。

## 9. Logging

所有写操作至少记录：

```text
actor
action
target
before/after reference
correlation_id
result
timestamp
```

日志不得写 Secrets 和真实敏感正文。

## 10. Branch / PR

遵循 `AGENTS.md` 和 `CONTRIBUTING.md`。

一个 Feature 一个分支，不在 main 直接开发。
