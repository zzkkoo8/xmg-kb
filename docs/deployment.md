# 部署规范

## 1. 原则

xmg-kb 不把所有上游产品重做成一个巨型自定义 Compose。优先复用官方部署方式，xmg-kb 只提供薄封装、统一生命周期命令和组件间 Adapter。

推荐：

```text
deploy/
├── bookstack/
├── prefect/
├── docling-serve/
├── mineru/
├── ragflow/
├── langfuse/
└── kag-poc/
```

项目自身服务建议独立：

```text
xmg-kb-api
xmg-kb-mcp
```

它们只封装领域逻辑和安全接口，不重写上游组件。

## 2. 版本锁

每个组件记录：

```text
version
image
digest
license
official_source
verified_at
```

生产长期禁止使用未锁定的 `latest`、`main`、`nightly`。

## 3. 运行数据

Runtime Data 必须在 Git checkout 外。

公开示例：

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

实际环境通过配置注入，不把真实路径写进公共仓库。

## 4. 服务分组

建议统一提供：

```text
bootstrap
up-core
up-ingestion
up-rag
up-interface
up-observability
status
verify
test
backup
restore
```

### Core

- BookStack；
- Prefect；
- xmg-kb API / MCP。

### Ingestion

- Docling Serve；
- MinerU；
- LibreOffice；
- ClamAV；
- Worker。

### RAG

- RAGFlow；
- Embedding / Rerank dependencies。

### Observability

- Langfuse。

### Optional POC

- KAG/OpenSPG。

## 5. 网络与接口边界

外部消费者优先只访问：

```text
xmg-kb API
xmg-kb MCP
```

不要让业务应用直接依赖 BookStack DB、RAGFlow DB、Prefect DB 或内部容器网络。

BookStack / RAGFlow 官方 API 由 Adapter 层封装，便于未来替换和权限控制。

## 6. 安全

- 数据库不公网暴露；
- Reverse Proxy 统一 TLS；
- 不共享 Admin Token；
- Wiki/API/MCP Token 使用最小权限；
- Runtime Secret 通过 `.env`/secret store 注入；
- `.env` 不进入 Git；
- 默认关闭匿名写入；
- 高风险 Canonical 操作默认不通过 MCP 暴露。

## 7. Health

每个 Required Component 至少有：

- Process/Container Health；
- API/CLI Smoke；
- Persistence Test；
- Restart Test。

“Container Up”不等于 Phase PASS。

Langfuse/KAG 等非当前主链阶段组件按 roadmap 定义是否阻塞当前 Gate。

## 8. Backup / Restore

必须分别定义：

- BookStack DB + Attachments；
- Prefect DB；
- RAGFlow Storage；
- xmg-kb State / Mapping；
- Langfuse Storage（启用后）；
- Config / Secrets；
- Canonical Export。

备份只有实际 Restore Drill 成功后才算有效。

## 9. 分发

Release Artifact 只能包含：

- Code；
- Public Docs；
- Deploy Templates；
- Migration/Schema Code；
- Synthetic Fixtures；
- Example Config。

不能包含生产知识、数据库、Index、Trace、内部报告或真实环境配置。