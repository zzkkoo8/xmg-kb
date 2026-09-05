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

## CanonicalArticle

```text
canonical_id
wiki_page_id
wiki_revision
title
vendor
product
topic
version_scope
review_status
content_sha256
```

## CanonicalSource

```text
canonical_id
source_document_id
source_section_id
knowledge_unit_id
relation
```

## RagMapping

```text
canonical_id
wiki_page_id
wiki_revision
rag_document_id
content_sha256
sync_status
active
last_sync_at
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
- Production Chunk 必须追溯至 Canonical Page + Revision；
- 同一 Canonical 的新旧 Revision 不应同时 Active。
