# 贡献指南

## 分支

禁止直接在 `main` 上开发。

使用：

- `feature/<name>`
- `fix/<name>`
- `docs/<name>`

## 开发前

阅读：

- `AGENTS.md`
- `CODEX-START.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/development.md`
- `docs/testing.md`
- `docs/publication-policy.md`

## 变更原则

- 优先使用成熟上游组件；
- 自定义代码保持薄层；
- 任何数据处理必须可重试、可恢复、幂等；
- Production RAG 只能来源于 Canonical Wiki；
- 新功能必须有测试；
- 公共仓库禁止真实知识和运行数据。

## Pull Request

PR 应说明：

- 目标；
- 当前 Phase；
- 设计依据；
- 修改范围；
- 测试证据；
- 风险；
- 回滚方法；
- 公共数据安全检查结果。

## 提交前

```bash
git diff --check
```

并运行：

- Unit Tests；
- 相关 Integration/Smoke Tests；
- Secret Scan；
- Public Repository Safety Check。

详见 `docs/testing.md` 和 `docs/publication-policy.md`。
