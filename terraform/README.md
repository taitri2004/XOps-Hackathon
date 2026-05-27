# XOps-Study Terraform — personal stack

Deploys the XOps-Study app into your personal AWS account in `ap-southeast-1`.
Covers 7 W7 mandatory capabilities. Bedrock Knowledge Base is created via Console
(5 min) because S3 Vectors Terraform support is still maturing.

## Prereqs (verify before applying)

- AWS account with MFA, Budget $80, Cost Anomaly Detection — done at pre-flight
- `aws configure` pointed at your account (NOT root keys) — verify with `aws sts get-caller-identity`
- Bedrock model access granted in `ap-southeast-1`: `anthropic.claude-3-5-haiku-20241022-v1:0` + `amazon.titan-embed-text-v2:0`
- Terraform >= 1.6

## Deploy — from repo root

```powershell
# 1. Build Lambda zip from app/ — see scripts/build.ps1
cd C:\Users\ADMIN\Downloads\XOps-Hackathon
.\scripts\build.ps1
# Output: build/lambda.zip (~15-25 MB)

# 2. Configure your terraform stack
cd terraform
copy terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set team = "G<N>" and owner = "<your-name>"

# 3. First apply — creates everything EXCEPT Bedrock KB
terraform init
terraform plan -out tfplan
terraform apply tfplan

# 4. Note the docs_bucket output. Create Bedrock KB in Console:
#    AWS Console → Bedrock → Knowledge bases → Create
#    - Data source: S3 → bucket from `terraform output docs_bucket`
#    - Embeddings model: amazon.titan-embed-text-v2:0
#    - Vector store: S3 Vectors (no minimum OCU cost)
#    - Chunking: Default (300 tokens, 20% overlap) — or note your override in docs/decision_blocks.md
#    Copy the KB ID after creation.

# 5. Second apply — wires KB ID into Lambda env
# Edit terraform.tfvars: bedrock_kb_id = "XXXXX"
terraform apply

# 6. Upload frontend to S3 (from repo root)
cd ..
aws s3 sync app/frontend/ s3://$(cd terraform; terraform output -raw frontend_bucket)/
```

## Verify (smoke test)

```powershell
cd terraform
$URL = terraform output -raw cloudfront_url
curl "$URL/api/health"

# Upload a sample doc to the docs bucket
cd ..
aws s3 cp app/sample_data/wiki_01_computer.txt s3://$(cd terraform; terraform output -raw docs_bucket)/test-user-001/manual-upload/

# Trigger KB sync in Console (one-time per data source change) — takes 1-2 min

# Query
curl -X POST "$URL/api/query" -H "X-User-Id: test-user-001" -H "Content-Type: application/json" `
  -d '{"question": "What is a computer?"}'
```

## Teardown (Sun 1/6 EOD — required deliverable)

```powershell
cd terraform
terraform destroy
# Then in AWS Console: delete the Bedrock KB you created manually
# Verify $0 charges accruing on Mon 2/6 → commit docs/teardown_confirmation.md
```

## What this stack does NOT include (and why — for the QnA)

| Skipped | Why |
|---|---|
| Cognito | Optional under W7 #7. Using `X-User-Id` header for demo. Document trade-off in `docs/decision_blocks.md`. |
| NAT Gateway | $1.08/day saved. All AWS-only egress via VPC Gateway+Interface Endpoints. |
| Multi-AZ RDS | DynamoDB used instead — single-key lookups don't need SQL. |
| KMS CMK | Using SSE-S3 default. Add CMK if you pick Optional #10 Advanced Security. |
| CloudWatch alarms/dashboard | Add `observability.tf` separately if you pick Optional #8. |
