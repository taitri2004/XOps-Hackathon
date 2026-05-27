# 🧠 XOps-Study — AI Study Buddy

W7 Capstone Hackathon submission. An AI-powered study platform: upload lecture notes,
ask grounded questions with citations, get auto-generated summaries and quizzes.

**Live demo URL:** _set after `terraform apply`_
**Domain:** EduTech (W7 Domain A)
**Region:** `ap-southeast-1` (Singapore)
**Cost cap:** $100 per personal account, target < $30 with clean teardown

---

## Repo layout

```
XOps-Hackathon/
├── app/                  FastAPI application (runtime-agnostic — runs locally, on Lambda, ECS, EC2)
│   ├── src/
│   │   ├── adapters/     AI / storage / userstore / vector — adapter pattern, swap via env vars
│   │   ├── app.py        FastAPI routes
│   │   ├── config.py     Env-driven config
│   │   └── handlers.py   Business logic (upload, query, summarize, quiz, delete)
│   ├── frontend/         Single-page HTML/JS UI (drag-drop upload, MCQ quiz, study history)
│   ├── sample_data/      Wikipedia text + test PDF for ingestion testing
│   ├── tests/            Smoke tests
│   ├── lambda_handler.py Mangum adapter — FastAPI → Lambda
│   └── requirements.txt
├── terraform/            IaC for AWS deployment (VPC + Lambda + API Gateway + S3 + DynamoDB + CloudFront)
├── scripts/
│   ├── build.ps1         Package Lambda zip (Linux manylinux wheels, strip bloat)
│   └── gen_test_pdf.py   Helper: synthesize a multi-page test PDF
└── docs/
    ├── W7_evidence.md         Graded artifact for Criterion IV
    ├── decision_blocks.md     §6.5 Decision blocks (anti-đối phó)
    ├── architecture.md        Final deployed architecture diagram
    └── teardown_confirmation.md  Committed after Sun 1/6 EOD teardown
```

---

## Quickstart — run locally (no AWS)

```powershell
cd app
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn src.app:app --reload --port 8000
```

Open http://localhost:8000 — the app runs with local SQLite + filesystem + AI stub.
Drag `sample_data/test_lecture.pdf` into the upload zone, ask a question, generate a quiz.

When ready to test against real AWS Bedrock, set in `.env`:
```
AI_BACKEND=bedrock
STORAGE_BACKEND=s3
USERSTORE_BACKEND=dynamodb
VECTOR_BACKEND=bedrock_kb
```
Plus the resource identifiers (bucket, table, KB ID).

---

## Deploy to AWS (~30 min)

Full deploy steps in [terraform/README.md](terraform/README.md). Short version:

```powershell
# 1. Pre-flight (one-time per personal AWS account):
#    - MFA on root
#    - Budget Alert $80 (confirm SNS email)
#    - Cost Anomaly Detection enabled
#    - Bedrock model access in ap-southeast-1: claude-3-5-haiku-20241022-v1:0 + titan-embed-text-v2:0

# 2. Build Lambda zip
.\scripts\build.ps1

# 3. Configure terraform variables
cd terraform
copy terraform.tfvars.example terraform.tfvars
# Edit: team = "G<N>", owner = "<your-name>"

# 4. First apply — provisions VPC, S3, DynamoDB, Lambda, API Gateway, CloudFront
terraform init
terraform apply

# 5. Create Bedrock Knowledge Base in Console (5 min):
#    Bedrock → Knowledge bases → Create
#    Data source: bucket from `terraform output docs_bucket`
#    Embeddings: amazon.titan-embed-text-v2:0
#    Vector store: S3 Vectors

# 6. Second apply — wire KB ID into Lambda env
# Edit terraform.tfvars: bedrock_kb_id = "<your-kb-id>"
terraform apply

# 7. Upload frontend to S3
cd ..
aws s3 sync app/frontend/ s3://$(cd terraform; terraform output -raw frontend_bucket)/

# 8. Verify
$URL = (cd terraform; terraform output -raw cloudfront_url)
curl "$URL/api/health"
# Open $URL in browser — drag-drop a PDF, ask questions, generate quiz
```

---

## Architecture summary (7 W7 mandatory capabilities)

| # | Capability | Service in this stack | Why |
|---|---|---|---|
| 1 | User-Facing Entry | **CloudFront** (HTTPS free on `*.cloudfront.net`) + **API Gateway v2 HTTP API** | No cert lifecycle to manage; cheapest API entry |
| 2 | Application Compute | **Lambda Python 3.12** + Mangum adapter for FastAPI | Pay-per-use, 1M req/month free tier |
| 3 | AI / ML Feature | **Bedrock Knowledge Base** + **Claude 3.5 Haiku** retrieve_and_generate | RAG grounds answers in user uploads; Haiku 12× cheaper than Sonnet |
| 4 | Data Persistence | **DynamoDB on-demand**, single-table (PK=user_id, SK=DOC#/QUERY#) | Single-key lookups for sessions; no JOIN needed |
| 5 | Object Storage | **S3** (docs bucket + frontend bucket), SSE-S3 | Standard, KB ingestion source, versioning on docs |
| 6 | Network Foundation | **VPC** + private subnets + Gateway Endpoint (S3, DDB) + Interface Endpoint (Bedrock) — **no NAT Gateway** | Saves $1.08/day; DB never public-facing |
| 7 | Identity & Access | **IAM least-privilege role** on Lambda + `X-User-Id` header (Cognito optional) | Hardcoded test user OK for hackathon per W7 docs |

**Optional capability attempted:** TBD (Full Observability / Advanced Cost Insights / Advanced Security — see Evidence Pack §6.5)

See [docs/architecture.md](docs/architecture.md) for the diagram.

---

## Teardown (mandatory by Sun 1/6 EOD)

```powershell
cd terraform
terraform destroy
# Console: also delete the Bedrock KB you created manually
# Mon 2/6: take Cost Explorer screenshot showing $0 accruing → commit docs/teardown_confirmation.md
```

---

## What's in this repo + what's NOT

| | Why |
|---|---|
| ✅ All code needed to redeploy from scratch | Reproducibility for grading |
| ✅ Terraform stack | Bonus Path E (IaC) |
| ✅ Build script for Lambda zip | Repeatable builds, no manual zip ritual |
| ✅ Sample data (wiki txt + generated PDF) | Trainer can verify retrieval works |
| ❌ `.venv/` | Per-machine virtualenv |
| ❌ `_data/` | Local SQLite + uploaded files |
| ❌ `terraform.tfvars` | Contains team-specific values |
| ❌ `*.tfstate*` | Terraform state — use local backend or set up remote backend |
| ❌ `build/` | Build artifacts — regenerable from source |
| ❌ `.env` | Secrets boundary |

---

## Credits

Built from the W7 StudyBot starter app provided in the course materials, then customized for the XOps-Study EduTech capstone.
UI is plain HTML+JS — no React build step.

Sample data: Wikipedia Simple English (CC-BY-SA 4.0) — see [`app/sample_data/SOURCES.md`](app/sample_data/SOURCES.md).
