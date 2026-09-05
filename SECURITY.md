# 安全策略

## 公共仓库安全

xmg-kb 公共仓库只保存软件与公开设计。

严禁提交：

- 密码、Token、Cookie、API Key；
- 私钥、生产证书；
- `.env`；
- 真实知识库文档；
- 生产数据库、索引、日志、Trace；
- 内部报告；
- 私有主机名、URL、真实部署路径；
- 客户或内部系统信息。

详细规则见 `docs/publication-policy.md`。

## 运行安全

生产部署应遵循：

- 最小权限；
- 独立服务账号；
- API Token 分角色；
- 数据库与内部服务不直接暴露公网；
- Wiki AI 账号默认只能读 Canonical、写 Review；
- Production RAG 只能索引已批准 Canonical；
- Raw Evidence 不允许被 Pipeline 原地修改；
- 所有写操作保留审计信息和关联 ID。

## 安全问题报告

请通过 GitHub 的私密安全报告机制提交潜在漏洞，不要在公开 Issue 中粘贴密钥、生产数据、内部地址或用户信息。
