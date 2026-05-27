# W7 Capstone Evidence Pack — Team G&lt;N&gt;

> Graded artifact for Criterion IV (40%). Fill in as you build, not Thursday night.

---

## 1. Cover

| | |
|---|---|
| **Team** | G&lt;N&gt; |
| **Members** | (names + Owner tags) |
| **Domain** | A — EduTech (AI Study Buddy) |
| **App name** | XOps-Study |
| **Repo** | https://github.com/taitri2004/XOps-Hackathon |
| **Live URL** | _set after `terraform apply`_ |
| **Total spend** | $X.XX (Cost Explorer Mon 2/6 screenshot) |
| **Region** | ap-southeast-1 |

---

## 2. Pitch & Vision

**Use case:** University students upload lecture slides → AI extracts 5 testable concepts,
generates 10-question MCQ quizzes, answers questions with citations back to specific slides,
and tracks study history per user. Cuts the "make my own flashcards from a 60-page deck"
busywork to 30 seconds.

**Target user:** University students cramming for exams; self-learners reviewing technical docs.

**Real-world parallel:** Quizlet AI · Khanmigo (Khan Academy AI tutor) · Coursera Coach · Google NotebookLM.

**Why this domain matters:** Education is the most universally relatable use case — every
interviewer was once a student. The Q&A-with-citations pattern is the same primitive that powers
internal-docs Q&A, customer support assistants, and legal research — so the architecture is
transferable.

---

## 3. Architecture

_(insert exported diagram from draw.io / excalidraw at `docs/architecture.png`)_

### Service decisions for the 7 mandatory capabilities

| # | Capability | Service | One-line rationale |
|---|---|---|---|
| 1 | UI entry | CloudFront + API Gateway HTTP API | HTTPS free on `*.cloudfront.net`; cheapest API entry |
| 2 | Compute | Lambda Python 3.12 + Mangum | 1M req/month free tier; pay-per-use |
| 3 | AI feature | Bedrock KB + Claude 3.5 Haiku retrieve_and_generate | RAG grounds answers in user uploads; Haiku ≈12× cheaper than Sonnet |
| 4 | Data persistence | DynamoDB on-demand single-table | All access is by user_id; no JOIN needed |
| 5 | Object storage | S3 (docs + frontend buckets), SSE-S3 | KB ingestion source; versioning on docs |
| 6 | Network | VPC + Gateway Endpoint (S3/DDB) + Interface Endpoint (Bedrock) | No NAT Gateway → saves $1.08/day |
| 7 | Identity baseline | IAM execution role + `X-User-Id` header | Cognito optional per W7; hardcoded test user is enough for demo |

### 2-3 trade-offs we consciously made

(Fill these in with concrete numbers — see `docs/decision_blocks.md` for the structured template.)

1. **S3 Vectors over OpenSearch Serverless** — saved ~$27 over 48h
2. **No NAT Gateway** — saved ~$2.16 over 48h, all egress via VPC Endpoints
3. **Lambda over ECS Fargate** — pay-per-use vs $X/day idle cost

---

## 4. Cost Discipline

Three Cost Explorer screenshots required (filtered by `Team=G<N>` tag):
- `docs/evidence/cost_day1.png` — Wed 27/5 EOD
- `docs/evidence/cost_day2.png` — Thu 28/5 EOD
- `docs/evidence/cost_friday.png` — Fri 29/5 pre-demo

### Top 3 cost drivers (fill after Day 2)

| Service | Cost | % of total |
|---|---|---|
| Bedrock Haiku tokens | $X.XX | XX% |
| VPC Interface Endpoint (Bedrock) | $0.62 | XX% |
| S3 Vectors | $0.0X | XX% |

### Trade-offs to stay lean (mandatory if claiming Bonus Path H < $30)

- Skipped NAT Gateway → −$2.16
- Single-AZ DynamoDB on-demand → tiny baseline cost
- Stripped boto3 from Lambda zip → faster cold start

---

## 5. Security

### IAM (required baseline)

- Lambda execution role: `xops-study-<owner>-lambda-role` — see `terraform/compute.tf`
- Granted actions (NO wildcards): `s3:GetObject/PutObject/DeleteObject/ListBucket` (docs bucket only),
  `dynamodb:GetItem/PutItem/UpdateItem/DeleteItem/Query` (userstore table only),
  `bedrock:InvokeModel/Retrieve/RetrieveAndGenerate/StartIngestionJob/GetIngestionJob`,
  `logs:CreateLogStream/PutLogEvents`, `cloudwatch:PutMetricData`
- Root MFA: enabled on Day 1
- Bucket Public Access Block: enabled on both buckets

### Optional #10 Advanced Security — chosen area: _(TBD)_

Pick ONE: Encryption (KMS CMK + rotation) · Audit (CloudTrail + Config) · Secrets (Secrets Manager) · Network (WAF / Flow Logs).

Document with measurement: rotation date, alarm count, blocked requests, etc.

---

## 6. Monitoring

- CloudWatch dashboard: `docs/evidence/dashboard.png` (Lambda invocations, errors, API 4xx/5xx, custom metric)
- Alarm config: `docs/evidence/alarm.png` (in OK or ALARM state — NOT INSUFFICIENT_DATA)
- Custom metric: `XOpsStudy/DocumentsIngested` published from Lambda after each upload
- Log Insights saved query: filter errors in last 1 hour

---

## 6.5 Measurement & Decisions ★

See [docs/decision_blocks.md](decision_blocks.md) for at least 2 structured DECISION blocks
with concrete numbers, alternatives considered, and trade-offs.

---

## 7. Lessons Learned (~200 words)

(Write this Friday morning after rehearsing the demo. Required topics:)
- What went well
- What you'd do differently
- One concrete failure case + how you mitigated it
- One question a Khanmigo / NotebookLM engineer would immediately ask about your architecture

---

## 8. Teardown

See [docs/teardown_confirmation.md](teardown_confirmation.md) — committed after Sun 1/6 EOD.

```powershell
cd terraform
terraform destroy
# Console: delete Bedrock KB manually (not in Terraform)
# Mon 2/6: Cost Explorer screenshot showing $0 charges accruing
```
