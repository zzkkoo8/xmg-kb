# 测试与验收

## 1. 测试分层

### Unit

覆盖：

- Schema；
- Policy；
- Pure Function；
- Mapping；
- Safety Checks。

### Integration

覆盖：

- BookStack API；
- Docling Serve；
- RAGFlow；
- Langfuse；
- State Store。

使用临时实例和合成数据。

### Smoke

覆盖：

```text
Source
→ Parse
→ Normalize
→ Governance
→ Review
→ Canonical
→ Chunk/Index
→ Retrieve
```

### Gold QA

用于评估：

- Retrieval；
- Citation；
- Faithfulness；
- Refusal；
- Version Isolation。

## 2. Parser Pilot

必须覆盖：

- Clean PDF；
- Scan PDF；
- Multi-column；
- Table；
- DOCX；
- PPTX；
- XLSX；
- Markdown；
- HTML。

验收：

- Retry；
- Resume；
- Failure Isolation；
- Provenance；
- Critical Fact 保留。

## 3. Document Governance

抽样验证：

- Exact Duplicate；
- Near Duplicate；
- Version；
- Metadata；
- Alias；
- Authority。

初始目标：

- Exact Duplicate Precision = 100%；
- Near Duplicate Precision >= 95%；
- Critical Wrong Version Merge = 0。

## 4. Knowledge Engineering

至少评估：

- KU Factual Precision；
- Source Traceability；
- Relation Precision；
- Conflict Recall；
- Canonical Quality。

初始目标：

- Traceability = 100%；
- KU Precision >= 98%；
- Critical Wrong Merge = 0；
- Relation/Alignment Precision >= 95%。

## 5. RAG Benchmark

至少比较：

```text
Full-text
Vector
Hybrid
Hybrid + Rerank
```

同时比较多个 Chunk Size 和结构策略。

初始目标：

- Top-5 Recall >= 95%；
- Critical Top-5 Recall >= 98%；
- Citation Correctness >= 95%；
- Correct Refusal >= 98%；
- Critical Hallucination = 0。

## 6. Failure Tests

至少模拟：

- Parser Crash；
- Worker Restart；
- Network Timeout；
- Wiki Down；
- RAG Index Failure；
- LLM Timeout；
- Duplicate Event；
- Disk Low；
- New Revision Index Fail。

## 7. Public Repository Test

提交前必须确认：

- 无 Secrets；
- 无真实文档；
- 无数据库；
- 无真实内部路径；
- 无内部 URL；
- 无运行 Trace；
- 无内部报告。

详见 `docs/publication-policy.md`。

## 8. Evidence

Phase PASS 的证据必须是：

- Test Output；
- API Result；
- Health Result；
- Metrics；
- DB Count；
- Reproducible Command。

“代码看起来正确”不是 PASS。
