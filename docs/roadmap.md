# xmg-kb 研发路线图：文件型知识库生产管线

当前优先级是生产高质量、可追溯、可持续治理的本地文件知识库。Wiki 展示和 GitLab 双向同步均暂缓，不得阻塞生产管线。

状态只允许：NOT_STARTED、IN_PROGRESS、IMPLEMENTED_UNVERIFIED、PASS、BLOCKED、DEVIATED。

## Phase 0 — Baseline & Safety
盘点代码、已有数据、历史产物、目录边界和公开/私有数据边界。原始来源只读；运行数据与 Git checkout 分离。

## Phase 1 — Inventory & Reuse
建立来源 Adapter、Manifest、稳定 Source ID、SHA-256、格式/大小/状态；优先复用高质量 Legacy 产物。支持增量运行、幂等、断点恢复，不重复处理未变化文件。

## Phase 2 — Multi-format Parsing
用代表性样本验证 Markdown、HTML、PDF、扫描 PDF、DOC/DOCX、PPT/PPTX、XLS/XLSX、图片/OCR 及多媒体资产。按格式和质量选择解析器；支持 fallback、失败隔离和逐文档重试。

## Phase 3 — Normalization & Provenance
产出统一 Markdown、必要的 HTML、独立 assets 和机器元数据。验证表格、代码、图片、链接、标题层级、关键事实和来源追溯；原始文件不被修改。

## Phase 4 — File Knowledge Store
确定本地知识目录、文件命名、稳定 ID、元数据 sidecar、资产路径和版本策略。知识文件为唯一 Canonical；解析缓存、状态、日志、隔离数据与 Canonical 目录分离。

## Phase 5 — Knowledge & Directory Governance
建立精确去重、近似重复候选、分类/别名、版本范围、权威性、冲突识别、知识拆分/合并建议和目录树评估。目录调整必须 dry-run、链接检查、diff、审计和回滚；近似重复不自动删除。

## Phase 6 — Agent Feedback Loop
定义统一反馈契约，接收 Agent 的 GOOD/WEAK/MISSING/CONFLICT/OUTDATED/FRAGMENTED 信号、任务引用和新证据。反馈生成 Proposal，经过证据验证、置信度/风险策略和审核后才修改 Canonical 文件；支持回滚。

## Phase 7 — API / MCP & Consumer Contract
通过稳定 API/MCP 提供文件搜索、读取、来源查询、知识提案、反馈提交和受控修订。不允许 Agent 任意写入/删除 Canonical 文件；所有变更经策略检查并审计。

## Phase 8 — RAGFlow Derived Index
从已审核 Canonical 文件构建 RAGFlow 索引；保存文件路径、hash、source IDs、知识版本与引用位置。增量更新幂等；新索引失败时保留上一有效版本。

## Phase 9 — Quality & Scale
先用 20–50 份代表性文档完成 smoke test，再逐批扩容。验证 retry/resume/idempotency、资产完整性、来源追溯、目录质量、反馈闭环和检索质量；通过证据决定是否扩大到全量。

## Future — Deferred Integrations
- Wiki/编辑 UI：只有在确认能原生读写本地 Canonical 文件后再做 POC。
- GitLab：未来实现文件双向同步、版本控制与备份；不是当前运行依赖。
- Knowledge Graph/KAG：只有对照实验显示明确收益后再引入。
- Multi-Agent 编排由外部 Agent 平台负责；xmg-kb 只接收反馈并提供知识接口。

## 退出标准
- 处理可重复运行、可恢复、幂等；
- 原始来源不被修改；
- Canonical 内容与资产完整落盘；
- 每份知识可追溯到来源；
- 目录变更可审计、可回滚；
- Agent 反馈进入治理闭环但不能无约束写入；
- RAG 可从 Canonical 文件重建；
- 不因 Wiki/GitLab 未部署而阻塞生产管线。
