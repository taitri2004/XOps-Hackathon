# Architecture — XOps-Study

> Final deployed architecture. Export the visual diagram to `architecture.png` and embed below.

## ASCII overview

```
                                                    [ Trainer's browser ]
                                                            │ HTTPS
                                                            ▼
                       ┌────────────────────── CloudFront ──────────────────────┐
                       │  Default origin: S3 (static frontend bucket)           │
                       │  /api/*  origin: API Gateway v2 HTTP API               │
                       └───────────────────┬───────────────────────┬────────────┘
                                           │                       │
                                ┌──────────▼──────────┐  ┌─────────▼──────────┐
                                │  S3 frontend bucket │  │ API Gateway HTTP   │
                                │  (private, OAC)     │  │ ANY /{proxy+}      │
                                └─────────────────────┘  └─────────┬──────────┘
                                                                   │
                                                                   ▼
                                          ┌────────────────────────────────────────┐
                                          │  Lambda (Python 3.12 + Mangum)         │
                                          │  - FastAPI app                         │
                                          │  - VPC: private subnet                 │
                                          │  - IAM least-privilege role            │
                                          └─┬──────────┬──────────┬─────────────┬──┘
                                            │          │          │             │
                              Gateway       │ S3       │ DDB      │ VPC IF EP   │
                              Endpoint  ◀───┘ Gateway  └──▶       └──▶          ▼
                                              EP             EP          ┌─────────────┐
                                                                         │  Bedrock    │
                                       ┌─────────┐    ┌────────────────┐ │  Knowledge  │
                                       │   S3    │    │   DynamoDB     │ │  Base       │
                                       │ docs    │    │  (single-table │ │  + Haiku    │
                                       │ bucket  │    │   user_id PK)  │ │  + S3 Vectors │
                                       └─────────┘    └────────────────┘ └─────────────┘
                                            │                                    ▲
                                            │ KB data source                     │
                                            └────────────────────────────────────┘
```

## Mandatory capability mapping

| W7 # | Service in diagram |
|---|---|
| 1 — User Entry | CloudFront (static) + API Gateway HTTP API (compute entry) |
| 2 — Compute | Lambda |
| 3 — AI | Bedrock KB retrieve_and_generate + Claude 3.5 Haiku |
| 4 — Data | DynamoDB single-table |
| 5 — Object Storage | S3 docs bucket (KB source) + S3 frontend bucket |
| 6 — Network | VPC + private subnets + Gateway/Interface Endpoints (no NAT) |
| 7 — Identity (baseline) | IAM execution role + X-User-Id header (Cognito optional) |

## Data flows

### Upload + ingest (POST /api/upload)

```
Browser ──multipart──▶ CloudFront /api/* ──▶ API GW ──▶ Lambda
                                                          │
                                                          ├─▶ S3 put_object → s3://docs-bucket/{user_id}/{doc_id}/{filename}
                                                          ├─▶ pypdf extract_text
                                                          ├─▶ Bedrock KB StartIngestionJob (async — KB picks up new S3 object)
                                                          └─▶ DynamoDB put_item (DOC#{doc_id} metadata)
```

### Query (POST /api/query)

```
Browser ──JSON──▶ CloudFront /api/* ──▶ API GW ──▶ Lambda
                                                    │
                                                    ├─▶ Bedrock retrieve_and_generate (user_id metadata filter, KB_ID)
                                                    │        │
                                                    │        ├─ retrieves top-K chunks from S3 Vectors
                                                    │        └─ Claude Haiku generates answer + citations
                                                    │
                                                    ├─▶ DynamoDB put_item (QUERY#{ts} log)
                                                    └─▶ JSON response → browser
```

### Summarize / Quiz (POST /api/summarize, /api/quiz)

```
Browser ──JSON {doc_id, n}──▶ ... ──▶ Lambda
                                       │
                                       ├─▶ DynamoDB Query → find filename for doc_id
                                       ├─▶ S3 get_object {user_id}/{doc_id}/{filename}
                                       ├─▶ pypdf extract (cap 8000 chars for token cost)
                                       ├─▶ Bedrock InvokeModel with structured-JSON prompt (Haiku)
                                       │        └─ returns JSON array (5 concepts OR n MCQ questions)
                                       ├─▶ _parse_json_array (tolerant — handles markdown fences)
                                       └─▶ JSON response → browser
```

## Why NOT certain services (will be probed in QnA)

| Skipped | Why |
|---|---|
| NAT Gateway | $1.08/day for nothing — Lambda only calls AWS services, VPC Endpoints suffice |
| Cognito | Optional per W7 #7. `X-User-Id` header from a hardcoded test user is enough for demo. Trade-off accepted: no per-user auth in production. |
| Multi-AZ RDS | DynamoDB used instead — single-key reads need no SQL |
| OpenSearch Serverless | S3 Vectors saves ~$27 over 48h with comparable retrieval quality at hackathon scale |
| KMS CMK | SSE-S3 default. Add only if Optional #10 = Advanced Security/Encryption path |
| CloudWatch alarms/dashboard | Add `observability.tf` only if Optional #8 chosen |

## What to draw in `architecture.png`

Use draw.io or excalidraw. Required elements:
- All boxes from the ASCII diagram above with AWS icons
- Color-code the 7 mandatory capability boxes (e.g. light-blue background)
- Color-code the 1 optional capability box (e.g. amber background)
- Arrows labeled with protocol (HTTPS / private VPC / IAM SigV4)
- Bottom legend: `Project=W7Capstone, Team=G<N>, Owner=<name>, Environment=hackathon`

Export PNG @1200px wide. Embed in this file:

```markdown
![Architecture](./architecture.png)
```
