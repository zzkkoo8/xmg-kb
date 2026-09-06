# xmg-kb

xmg-kb 是一套面向技术资料的开源知识工程方案，目标是把 PDF、Office、Markdown、HTML 等异构资料，持续治理为：

1. **人类可读、可编辑、易维护的技术 Wiki**；
2. **AI 可检索、可引用、可受控编辑的 Canonical Knowledge**；
3. **高质量、可增量更新的 RAG 检索索引**。

项目坚持“成熟开源组件优先、少量胶水代码、自托管、可复现、可审计”的原则。

## 核心架构

```text
Evidence Sources
      ↓
Source Registry / Manifest
      ↓
Prefect
      ↓
Docling Serve ──→ MinerU fallback
      ↓
Normalize / Dedup / Version / Provenance
      ↓
Knowledge Governance
      ↓
Outline 90-Review
      ↓
Outline Canonical Collections
      ↓
RAGFlow Parser → Chunker → Indexer
      ↓
Metadata Filter → Hybrid Retrieval → Rerank
      ↓
AI QA
      ↓
Langfuse Feedback / Evaluation
      ↓
Knowledge Evolution → Review
```

KAG/OpenSPG 作为 Knowledge Engineering 加速器进行 POC，对比简单 Curator 基线；只有真实数据评测证明收益明显时才进入长期主链。

## 设计原则

- **Wiki 与 RAG 分层**：Wiki 保存人类维护的 Canonical Knowledge；RAGFlow 只保存派生检索索引。
- **Evidence 与 Canonical 分层**：原始资料不是正式知识，Production RAG 不直接索引 Raw。
- **Knowledge Unit 与 RAG Chunk 分离**：前者用于治理、去重、版本和冲突；后者用于检索。
- **增量优先**：重复资料不重复解析，内容未变化不重复调用昂贵模型。
- **可追溯**：每篇 Canonical Article、每个检索 Chunk 都能反查来源与版本。
- **Review Gate**：AI 默认只能创建或修改 Review 内容，不能绕过审核静默覆盖正式知识。
- **成熟组件优先**：不自研 Wiki、OCR、PDF 布局引擎、Workflow Runtime、Vector DB、Trace/Eval 平台。
- **公共仓库零内部数据**：本仓库只保存公开设计、源码、配置模板、测试和部署说明。

## 默认组件

| 能力 | 组件 | 角色 |
|---|---|---|
| Human Wiki | Outline | Canonical Wiki / Review |
| Workflow | Prefect | Retry / Resume / Cache / Schedule |
| 主解析 | Docling Serve | 异步文档解析 |
| 复杂文档兜底 | MinerU | OCR / 复杂布局 / 表格 / 公式 |
| RAG | RAGFlow | Parser / Chunker / Indexer / Retrieval |
| Trace & Eval | Langfuse | Trace / Feedback / Dataset / Evaluation |
| Knowledge Engineering | Simple Curator + KAG POC | KU / Alignment / Conflict / Canonical |
| AI Wiki 接口 | Outline API/MCP + Webhook Adapter | 安全 AI 读写与状态同步 |
| 本地状态 | SQLite / PostgreSQL（按规模） | Pipeline state |

## Codex 开局

新的 Codex / Agent **不要直接写代码**。按以下顺序阅读：

1. [`AGENTS.md`](AGENTS.md)
2. [`CODEX-START.md`](CODEX-START.md)
3. [`docs/requirements.md`](docs/requirements.md)
4. [`docs/architecture.md`](docs/architecture.md)
5. [`docs/roadmap.md`](docs/roadmap.md)
6. [`docs/component-audit.md`](docs/component-audit.md)
7. [`docs/development.md`](docs/development.md)
8. [`docs/testing.md`](docs/testing.md)
9. [`docs/publication-policy.md`](docs/publication-policy.md)

然后只推进当前最靠前、前置条件已满足但尚未 PASS 的 Phase。

## 仓库边界

本仓库可以包含：

- 架构与设计文档；
- 源代码；
- Schema、Prompt 模板；
- 合成测试数据；
- Docker/Compose/Helm/Make 等部署模板；
- CI；
- 公共运维与开发文档。

本仓库禁止包含：

- 真实技术资料、PDF/Office 文档；
- 生产 Wiki 导出；
- 解析后的真实语料；
- RAG Chunk / Vector Index；
- 数据库、运行状态、Trace、日志、备份；
- Token、密码、Cookie、证书私钥；
- 私有主机名、内部 URL、真实部署路径；
- 任何客户、内部系统或生产环境敏感信息。

详见 [`docs/publication-policy.md`](docs/publication-policy.md)。

## 文档索引

- [需求基线](docs/requirements.md)
- [总体架构](docs/architecture.md)
- [研发路线图](docs/roadmap.md)
- [组件审计](docs/component-audit.md)
- [历史设计审计](docs/design-audit.md)
- [数据模型](docs/data-model.md)
- [开发规范](docs/development.md)
- [部署规范](docs/deployment.md)
- [测试与验收](docs/testing.md)
- [公共仓库发布规范](docs/publication-policy.md)
- [架构决策记录](docs/decisions/README.md)

## 当前状态

当前仓库首先固化**公开架构基线和 Codex 开发规范**。真实运行状态、内部数据进度和私有审计结果不进入公共仓库。

## License

xmg-kb 自有代码的项目许可证在首次软件发布前单独确定。第三方组件继续遵循各自许可证。
