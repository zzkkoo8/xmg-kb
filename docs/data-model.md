# 数据模型

本文件定义逻辑数据契约。具体数据库实现可以演进，但字段语义必须保持稳定。

## RawSource

```text
source_id
source_uri
content_sha256
size
mime
observed_at
source_type
```

## Document

```text
document_id
source_id
title
vendor
product
component
version
authority
lifecycle
parser
parser_version
parse_status
parse_quality
```

## Section

```text
section_id
document_id
heading_path
page_start
page_end
text_hash
```

## KnowledgeUnit

```text
unit_id
section_id
type
title
claim
condition
procedure
result
vendor
product
component
version_scope
authority
```

## KnowledgeRelation

```text
relation_id
unit_a
unit_b
relation_type
confidence
evidence
review_status
```

`relation_type`：

- equivalent
- supplements
- supersedes
- version_specific
- conflicts
- example_of
- unrelated

## Conflict

```text
conflict_id
claim_a
claim_b
scope_a
scope_b
status
resolution
```

## CanonicalFile

```text
knowledge_id
relative_path
format
content_sha256
asset_refs
source_ids
taxonomy
version_scope
review_status
confidence
created_at
updated_at
```

## CanonicalSource

```text
knowledge_id
source_document_id
source_section_id
knowledge_unit_id
relation
```

## RagMapping

```text
knowledge_id
relative_path
content_sha256
rag_document_id
index_revision
sync_status
active
last_sync_at
```

## FileAsset

```text
asset_id
relative_path
mime
content_sha256
size
referenced_by
source_ids
```

## KnowledgeChange

```text
change_id
knowledge_id
action
before_hash
after_hash
reason
evidence_refs
actor
risk
review_status
rollback_ref
created_at
```

## AgentFeedback

```text
feedback_id
source_agent
task_ref
knowledge_refs
signal_type
evidence_refs
observed_problem
proposal
confidence
risk
status
created_at
```

## EvolutionEvent

```text
event_id
event_type
topic
priority
evidence_refs
canonical_id
status
created_at
```

## 约束

- 未知值必须显式为 unknown/null，不允许模型编造；
- Canonical 必须至少追溯至 Source Document；
- Production Chunk 必须追溯至 Canonical File + Content Hash；
- 同一知识项的旧新索引版本不应同时 Active。
