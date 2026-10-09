# ADR-0004：文件型知识库作为唯一 Canonical Store

- Status: Accepted
- Date: 2026-10-09

## Context

xmg-kb 需要处理多来源、多格式知识，并支持本地文件操作、批量治理、可追溯、RAG、Agent 反馈闭环和未来同步/备份。Wiki 内置数据库会引入第二份内容事实源，并使知识恢复依赖特定应用。

## Decision

1. 本地文件系统是唯一 Canonical Knowledge Store。
2. Markdown 是主要结构化知识格式；必要时保留 HTML，图片、视频、PDF、Office 和其他附件作为真实文件保存。
3. 元数据、来源映射、任务状态和临时解析产物与 Canonical 正文分离。
4. 原始 Evidence 默认只读；处理失败必须可重试、隔离和审计。
5. RAG 索引是可重建派生数据。
6. Agent 反馈先进入 Proposal/治理流程，不允许无约束写入 Canonical 文件。
7. Wiki UI 和 GitLab 双向同步暂缓。未来 Wiki 必须原生读写本地文件；GitLab 仅作为同步、版本控制和备份目标。
8. 保留 SourceAdapter、ParserAdapter、KnowledgeStore/File API、RagAdapter 等薄边界；不提前开发多个 Wiki Adapter。

## Alternatives

- Wiki 数据库作为 Canonical：拒绝，因为知识无法独立于 Wiki 应用原生操作和恢复。
- Markdown 导入 Outline/BookStack/Wiki.js 后由应用保存：拒绝作为主存储，因为会形成数据库副本。
- GitLab 作为当前知识运行时：延期；当前先验证本地生产管线，避免引入不必要依赖。

## Consequences

- 文件可以直接使用常见工具检查、编辑、diff、备份和迁移。
- 必须严谨处理文件 ID、相对链接、资产路径、并发写入、原子替换、审计和回滚。
- RAG、搜索和未来 UI 都必须消费 Canonical 文件，而非反向成为事实源。
- GitLab 同步冲突和双向同步策略留到后续 ADR。

## Validation

使用 20–50 份代表性样本验证多格式解析、资产完整性、provenance、幂等/恢复、目录治理、Agent 反馈和索引重建。

## Rollback

此决策可通过新的 ADR 修订；在替换 Canonical Store 前必须完成全量导出、hash 校验、引用检查和恢复演练。
