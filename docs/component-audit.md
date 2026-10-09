# 组件选型审计

## 1. 选型标准

按自托管、成熟度、维护活跃度、许可证、稳定接口、运维成本、数据可迁移性和可替换性评估。优先采用成熟组件，避免为追求抽象而自研重复基础设施。

## 2. Canonical Knowledge Store：本地文件系统

结论：当前唯一 Canonical Store。

- Markdown 是主要结构化知识格式。
- 必要时保留 HTML；图片、视频、音频、PDF、Office 和附件作为真实文件保存。
- 元数据、来源映射、任务状态与正文分离。
- 其他应用必须能直接读取和修改原文件。
- RAG 索引是派生数据，可从 Canonical 文件重建。
- GitLab 同步/备份属于后续阶段，不是当前运行依赖。

Outline、BookStack、Wiki.js 等数据库型 Wiki 不进入当前主链。只有未来 POC 证明编辑会直接修改本地 Canonical 文件、媒体资产不丢失、离线可恢复时，才重新评估展示层。

## 3. Workflow：Prefect

采用 Prefect 管理确定性 Flow/Task、Retry、Cache、Schedule、Concurrency 和可恢复状态。xmg-kb 不自研 Workflow Runtime；业务判断进入 Policy，组件调用进入 Adapter。

## 4. Document Parsing

### Docling Serve
候选主 Parser，采用异步任务模式。需以代表性样本验证解析质量、吞吐和部署约束。

### MinerU / OCR
作为特定复杂 PDF、扫描件、表格、公式或低质量解析结果的 fallback，不对所有文档无条件运行。

### LibreOffice
用于需要标准化转换的 Office 文档。

### ClamAV
用于 Evidence 扫描，不得自动修改或删除原始文件。

解析器选择必须通过样本测试；不将单一引擎写死为所有格式的唯一通道。

## 5. RAG：RAGFlow

RAGFlow 是 Canonical 文件的派生索引与检索层，负责解析/切块/索引/检索能力。正式数据集只接收通过质量门禁的 Canonical 文件；Raw、临时解析结果和未审核 Proposal 不得直接进入正式索引。

xmg-kb 不自研第二套 Vector DB、Chunk Engine 或 Hybrid Search Engine。

## 6. Observability / Evaluation：Langfuse

作为 Trace、Feedback、Dataset、Experiment 和 Evaluation 能力。反馈是治理信号，不是知识事实源；敏感正文按最小必要原则处理。

## 7. Knowledge Engineering

MVP 采用薄的规则与模型协同流程：Section → Knowledge Unit → Candidate → Relation/Conflict → Proposal。Knowledge Unit 用于知识治理，RAG Chunk 用于检索，不能混用。

KAG/OpenSPG 仅作为可选 POC。只有同数据集 Benchmark 证明明显收益且维护成本合理时才引入。

## 8. API / MCP

xmg-kb API/MCP 提供受控文件搜索、读取、来源查询、反馈提交和知识变更提案。所有写操作经过治理策略，不能让 Agent 任意写路径或绕过审计直接删除/覆盖 Canonical 文件。

## 9. Adapter 基线

```text
SourceAdapter
ParserAdapter
FileStore / File API
RagAdapter
ObservabilityAdapter
```

当前不实现 WikiAdapter。未来展示层若通过硬性 POC，再以薄 Adapter 接入，不侵入知识治理核心。

## 10. Packaging

采用锁定版本的上游组件、独立部署模板、项目 CLI/Make、合成测试数据、示例配置、CI 和公共仓库安全检查。不要 fork 上游产品形成私有发行版，除非独立 ADR 证明必要。
