# Teardown Confirmation — Sun 1/6/2026

> Required deliverable. Commit this file after running `terraform destroy` + manual KB delete.

## Resources deleted

- [ ] `terraform destroy` exit code 0 (all TF-managed resources gone)
- [ ] Bedrock Knowledge Base manually deleted via Console
- [ ] CloudWatch Log Group `/aws/lambda/xops-study-<owner>-api` deleted (TF retains by default — manual cleanup)
- [ ] S3 buckets emptied + deleted (TF `force_destroy = true` handles this)
- [ ] No orphan EBS volumes / snapshots
- [ ] No orphan ENIs from Lambda VPC config (sometimes lag 10-15 min after destroy — verify)

## Cost Explorer confirmation

Take screenshot Mon 2/6 morning showing `Team=G<N>` filter = **$0.00 accruing**.

Embed below:

```markdown
![Teardown confirmed](./evidence/teardown_zero_cost.png)
```

## What stayed billable after teardown (if anything)

(Document any residual charges and why — e.g. KMS CMK 7-day deletion grace period.)

## Final repo state

| Branch | Status |
|---|---|
| `main` | Tagged `v1.0-demo` at Demo Day commit |
| Personal AWS account | Resources: 0 active |
| Repo visibility | Public (keep for portfolio) |
