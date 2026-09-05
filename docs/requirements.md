# 需求基线

## 1. 产品目标

xmg-kb 最终提供两种核心产品形态：

1. **Human Wiki**：人类可读、可编辑、可分类、可评论、可维护；
2. **AI Knowledge Base**：AI 可快速检索、引用，并能通过受控流程辅助编辑 Wiki。

## 2. 输入资料

系统面向：

- Markdown / HTML；
- PDF；
- DOC/DOCX；
- PPT/PPTX；
- XLS/XLSX；
- 图片与扫描件；
- 历史已整理 Markdown；
- 厂商手册、FAQ、培训、版本说明、故障案例等。

## 3. Human Wiki

必须满足：

- 浏览器访问；
- WYSIWYG 与 Markdown；
- 层级目录；
- 搜索；
- Tags；
- 附件；
- 评论；
- 页面历史；
- 权限；
- Import / Export；
- 稳定 API；
- 备份/恢复。

## 4. AI Knowledge Management

AI 必须能够：

- Search；
- Read Full Page；
- Read Source Metadata；
- Create Review；
- Patch Review；
- Comment；
- 提出分类/目录建议。

默认禁止：

- Delete Canonical；
- 绕过审核；
- 无证据改变关键参数；
- 静默解决版本或冲突。

## 5. 海量资料管线

必须：

- 批量；
- Retry；
- Resume；
- Incremental；
- Idempotent；
- Concurrency Limited；
- 可监控状态；
- 可按文档重跑；
- 优先复用已处理结果；
- Parser 失败有 fallback；
- 全程保留 Provenance。

## 6. Knowledge Governance

至少包含：

- Exact Dedup；
- Near-document Dedup；
- Metadata；
- Taxonomy / Alias；
- Version Scope；
- Authority；
- Security Classification；
- Knowledge Unit；
- Knowledge-level Relation；
- Conflict；
- Canonicalization。

## 7. RAG

Production RAG 必须：

- 只来源于 Canonical Wiki；
- 有正式 Chunking；
- Chunk 可追溯至 Page + Revision；
- Metadata Filter；
- Full-text；
- Vector；
- Hybrid；
- Rerank；
- Incremental Update；
- Revision Atomic Switch；
- Citation。

## 8. 质量

初始目标：

- Canonical Source Traceability = 100%；
- Critical Wrong Merge = 0；
- Top-5 Retrieval Recall >= 95%；
- Critical Top-5 Recall >= 98%；
- Citation Correctness >= 95%；
- Correct Refusal >= 98%；
- Critical Hallucination = 0。

阈值应通过真实 Gold QA 持续校准。

## 9. 自进化

真实使用信号至少分类：

- `GOOD`
- `WEAK`
- `MISSING`
- `CONFLICT`
- `OUTDATED`
- `FRAGMENTED`

系统可以自动发现、聚类、找证据、生成 Proposal，但关键事实变化必须 Review。

## 10. 工程要求

- 自托管；
- 开源成熟组件优先；
- 组件版本可锁定；
- 开发环境可复现；
- 公共代码可在无任何私有知识数据情况下安装和测试；
- 组件可独立升级；
- 不依赖私有目录结构；
- 公共仓库零内部数据。
