# 文件型知识库生产管线

## 1. 决策

xmg-kb 当前优先建设文件型知识库生产管线，暂缓 Wiki 展示/编辑层与 GitLab 同步。

**本地文件系统是唯一 Canonical Knowledge Store。** 知识正文、多媒体和附件以真实文件形式保存；数据库、搜索引擎、RAG 索引和 GitLab 都不能成为唯一知识原文。

- Markdown：主要结构化知识格式。
- HTML：保留需要 HTML 语义或无法无损转换的内容。
- Assets：图片、图表、视频、音频及其他附件以独立文件保存。
- 原始 PDF、Office、扫描件等可作为只读 Evidence，也可按治理规则作为知识附件保留。
- Metadata：来源、哈希、解析器版本、权限、版本范围、置信度和治理状态，与正文分离存储。
- GitLab：未来用于文件双向同步、版本控制和备份；当前不作为运行依赖。
- Wiki：当前不实现。未来展示/编辑应用必须原生读取并修改 Canonical 原文件，不能仅把内容导入自己的数据库后形成副本。

## 2. 端到端管线

```text
Local / Network / Web / API / Office / PDF / Image / Human / Agent
                              |
                              v
                    Source Adapter + Manifest
                              |
                              v
                 Inventory / Hash / Reuse / Dedup
                              |
                              v
                    Parser Adapter + Fallback
                              |
                              v
                  Normalize: Markdown + Assets
                              |
                              v
           Knowledge Build: Classify / Split / Merge / Link
                              |
                              v
                  Local File Knowledge Store
                              |
                              v
             Directory / Quality / Provenance Governance
                              |
                 +------------+-------------+
                 |                          |
                 v                          v
             Knowledge API               RAGFlow
                 |                     Derived Index
                 v                          |
           External Agents <----------------+
                 |
                 v
        Feedback / Evidence / Corrections
                 |
                 v
         Knowledge Proposal Queue
                 |
                 +-------> Knowledge Build
```

## 3. 推荐目录布局

实际路径通过配置指定；以下只是公开示例，不是固定部署路径。

```text
/srv/xmg-kb/
├── sources/       # Source manifest 和来源引用
├── work/          # 临时解析/转换结果，可重建
├── knowledge/     # Canonical 知识文件
│   ├── README.md
│   ├── 产品/
│   ├── 技术/
│   ├── 运维/
│   ├── API/
│   ├── FAQ/
│   └── assets/
├── metadata/      # provenance、hash、taxonomy、质量与变更映射
├── state/         # checkpoint、任务状态、重试信息
├── quarantine/    # 损坏、不可解析、可疑或需人工处理的内容
└── logs/          # 运行日志
```

必须区分原始 Evidence、临时解析结果和 Canonical 知识。不得把真实知识数据、运行状态、日志或内部路径提交到公共 GitHub 仓库。

## 4. 多来源与多格式

所有来源先转换为统一 Manifest 记录，再进入处理管线。Source Adapter 负责接入差异，不在核心流程中写死来源类型。

每份来源至少记录稳定 Source ID、URI/来源描述、SHA-256、大小、MIME/格式、发现时间、来源类型和处理状态。原始来源默认只读。

解析器按格式、文档特征和质量选择；Docling Serve 作为候选主解析器，MinerU/OCR 用于合适的复杂 PDF/扫描件，LibreOffice 用于需要转换的 Office 文件。实际选择必须由小样本质量和部署验证决定，不得将某个解析器写死为所有格式的唯一通道。

失败必须可分类、重试、隔离和单文档重跑。禁止静默跳过失败。

## 5. Canonical 文件和资产

Canonical 文件应可由普通文件工具读取、编辑、diff、备份和迁移，不依赖 Wiki 数据库才能恢复。

每篇知识应有稳定 ID 或稳定映射；文件路径可因目录治理调整，但路径变化必须更新映射并验证引用。Markdown 中的图片、附件使用可移植的相对路径或受控 URI。任何外部资源都不能成为唯一副本。

机器元数据至少支持：
- source IDs 与 provenance；
- 原始内容和标准化内容的 SHA-256；
- parser 与 parser version；
- 处理时间和质量状态；
- taxonomy、aliases、product/version scope；
- authority、security classification、confidence；
- 当前治理状态、变更记录和回滚引用。

## 6. 目录树治理

目录树是持续治理对象，不是一次性自动分类结果。系统应识别重复/重叠目录、主题混杂、层级过深、孤儿文件、命名不一致、断链和资产缺失。

调整流程：
1. 分析目录和内容分布；
2. 生成目录变更 Proposal，说明证据和影响；
3. Dry-run，生成移动/重命名计划；
4. 校验内部链接、图片和附件引用；
5. 展示 Diff 并按风险决定自动执行或人工批准；
6. 执行后验证并保留回滚信息。

近似重复只进入候选队列；不得根据模型相似度直接删除原文件。

## 7. Agent 使用后的反哺闭环

外部 Agent 可以提交使用反馈、新证据、缺失知识、冲突、过期信息和修正建议。反馈不是 Canonical 内容，不能直接覆盖知识文件。

反馈至少包含 feedback ID、source agent、task/conversation reference、knowledge/file IDs、signal type、evidence references、observed issue、proposal、confidence、risk、status 和 timestamps。

信号类型：
- GOOD：知识有效；
- WEAK：内容不足或不够清晰；
- MISSING：缺少所需知识；
- CONFLICT：不同来源或实际结果不一致；
- OUTDATED：疑似过期；
- FRAGMENTED：相关知识分散。

闭环为：Agent 使用 → 反馈/新证据 → 聚类与验证 → Knowledge Proposal → Policy/Confidence/Risk → 低风险自动处理或人工审核/隔离 → 修改 Canonical 文件 → 校验来源与链接 → 重新索引 → 后续效果评估。

模型生成的回答本身不能自动视为事实证据。执行结果、权威来源、人工确认和可复现测试应作为证据等级更高的依据。

## 8. API 与安全边界

当前 API/MCP 先支持受控读取、搜索、来源查询、反馈提交和变更提案。任何 Canonical 写入都必须经过统一的治理服务，而不是让 Agent 任意写文件路径。

- 路径访问必须限制在配置的知识根目录，防止路径穿越。
- 默认禁止任意删除、覆盖和批量移动。
- 写操作记录 actor、action、target、before/after hash、reason、evidence、correlation ID、result 和 timestamp。
- 高风险修改、冲突解决和大规模目录调整需要人工确认。
- 失败操作应幂等且可恢复；不要用 catch-all 隐藏错误。

## 9. RAG

RAGFlow 只消费通过质量门禁的 Canonical 文件，生成可重建的派生索引。索引记录必须能追溯到文件路径/稳定 ID、内容 hash、来源和知识版本。新版本索引失败时保留上一有效版本。

知识文件是事实源，RAG Chunk 只是检索单元。不能把解析片段直接提升为 Canonical 知识。

## 10. GitLab 与 Wiki 的后续边界

GitLab 同步/备份属于后续阶段，不阻塞本地生产管线。未来同步需定义冲突检测、来源优先级、双向变更、删除保护、重试、审计和灾难恢复。

未来 Wiki/编辑 UI 必须通过 POC 证明：人类编辑会直接修改本地 Canonical 文件；多媒体仍以文件形式保存；离线可恢复；路径/链接和元数据不丢失。仅支持导入/导出或将页面保存在内置数据库的产品不满足硬性定义。

## 11. 第一阶段验收

先用 20–50 份代表性样本完成端到端验证，再扩大批次：
- 多来源 inventory、hash、复用和幂等；
- Markdown、HTML、PDF、扫描件、Office、图片及附件解析；
- 图片/表格/代码/链接/关键事实不无故丢失；
- Retry、Resume、单文档重跑和失败隔离；
- Canonical 文件与 assets 真正落盘；
- 每份知识可追溯到来源；
- 目录调整可预览、审计和回滚；
- Agent 反馈可产生 Proposal，不会无约束覆盖知识；
- RAG 索引可从 Canonical 文件重建；
- 原始 Evidence 未被修改。
