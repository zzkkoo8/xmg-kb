# 部署规范

## 1. 原则

xmg-kb 不把所有上游产品重做成一个巨型自定义 Compose。

推荐：

```text
deploy/
├── outline/
├── prefect/
├── docling-serve/
├── mineru/
├── ragflow/
├── langfuse/
└── kag-poc/
```

优先复用各项目官方部署方式。

## 2. 版本锁

每个组件记录：

```text
version
image
digest
license
official source
verified_at
```

禁止生产长期使用：

```text
latest
main
nightly
```

## 3. 运行数据

Runtime Data 必须在 Git checkout 外。

示例：

```text
/srv/xmg-kb/
├── evidence/
├── state/
├── work/
├── databases/
├── indexes/
├── logs/
└── backups/
```

这只是公开示例路径，实际环境通过配置注入。

## 4. 服务分组

建议统一提供：

```text
bootstrap
up-core
up-ingestion
up-rag
up-observability
status
verify
backup
restore
```

### Core

- Outline；
- Prefect；
- Project API/MCP Adapter。

### Ingestion

- Docling Serve；
- MinerU；
- Worker。

### RAG

- RAGFlow；
- Embedding/Rerank dependencies。

### Observability

- Langfuse。

## 5. 安全

- 数据库不公网暴露；
- Reverse Proxy 统一 TLS；
- 不共享 Admin Token；
- Wiki AI Token 使用最小权限；
- Runtime Secrets 通过 `.env`/secret store 注入；
- `.env` 不进入 Git；
- 默认关闭公共匿名写入。

## 6. Health

每个组件至少有：

- Process/Container Health；
- API Health；
- Persistence Test；
- Restart Test。

“Container Up”不等于 Phase PASS。

## 7. Backup / Restore

必须分别定义：

- Wiki DB + Assets；
- Prefect DB；
- RAGFlow Storage；
- Langfuse Storage；
- State / Mapping；
- Config / Secrets；
- Canonical Export。

备份只有实际 Restore Drill 成功后才算有效。

## 8. 分发

Release Artifact 只能包含：

- Code；
- Public Docs；
- Deploy Templates；
- Migration/Schema Code；
- Synthetic Fixtures。

不能打包生产知识或数据库。
