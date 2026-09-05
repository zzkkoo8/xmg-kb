# 公共仓库发布规范

本仓库是公开仓库。

原则：

> 只公开软件、架构、模板和合成测试数据；不公开任何真实知识内容或运行数据。

## 1. 允许提交

- 公开架构设计；
- 源代码；
- Schema；
- Prompt 模板；
- Unit/Integration Tests；
- Synthetic Fixtures；
- Docker/Compose/Helm/Make 等模板；
- `.env.example`；
- 公共版本/许可证清单；
- 通用运维文档；
- Mermaid / 审核后的 SVG；
- Benchmark 方法和合成 Benchmark 数据。

## 2. 禁止提交

绝对禁止：

- 真实知识库 Source Documents；
- 私有厂商/客户/内部手册；
- Parsed/Normalized 真实语料；
- Production Wiki Export；
- RAG Chunk / Vector Index；
- Database Dump；
- Runtime State DB；
- 真实 Logs / Trace；
- 内部审计报告；
- Password / Token / Cookie / API Key；
- Private Key；
- `.env`；
- 私有主机名、内部 URL；
- 真实部署绝对路径；
- 客户/内部系统信息；
- 内部截图；
- Backup / Archive。

## 3. 示例规范

公共文档只使用：

```text
/srv/xmg-kb
/srv/xmg-kb/evidence
https://wiki.example.invalid
https://rag.example.invalid
```

不得把真实运行环境路径复制进仓库。

## 4. 数据分离

```text
Git Checkout
  → code / docs / templates

External Runtime Root
  → evidence
  → parsed
  → normalized
  → databases
  → indexes
  → logs
  → backups
```

软件不得要求私有知识文件必须位于 Git checkout 内。

## 5. Pre-push Gate

至少：

1. Tests；
2. `git diff --check`；
3. Secret Scan（如 Gitleaks）；
4. Forbidden Path/Hostname Scan；
5. Binary Review；
6. `git status --short`；
7. Generated Knowledge Artifact Check。

任一失败：

```text
PUBLICATION_GATE: BLOCKED
```

## 6. Binary Default Deny

默认忽略常见：

- PDF；
- Office；
- Archive；
- Database；
- Image；
- Runtime Artifacts。

公共示意图优先使用 Mermaid 或人工审核后的文本型 SVG。

## 7. Release

Release 可以包含：

- Code；
- Public Deploy Manifest；
- Schema/Migration Code；
- Synthetic Fixture；
- Templates；
- Public Docs。

Release 不得包含：

- Runtime Evidence；
- Production Knowledge；
- Production DB；
- Index；
- Trace。
