# NOTE: Bedrock Knowledge Base creation in Terraform requires the AWS provider to
# support the S3 Vectors storage type (provider >= 5.70 has aws_bedrockagent_knowledge_base
# but S3 Vectors backend support may lag). For hackathon speed, the recommended path is:
#
#   1. terraform apply (creates VPC + S3 + DDB + Lambda + API GW + CloudFront — NOT the KB)
#   2. Create the Bedrock Knowledge Base via AWS Console (5 min):
#        - Data source: aws_s3_bucket.docs (output: docs_bucket)
#        - Embeddings: amazon.titan-embed-text-v2:0
#        - Vector store: S3 Vectors (no minimum cost)
#        - Chunking: Default (300 tokens, 20% overlap) — change in Decision §6.5 if you tune
#   3. Set the KB ID into terraform.tfvars: bedrock_kb_id = "XXXXX"
#   4. terraform apply again (updates Lambda env var BEDROCK_KB_ID)
#
# If you want to attempt full IaC for Bonus Path E, switch the block below to
# aws_bedrockagent_knowledge_base + aws_bedrockagent_data_source AFTER verifying
# your provider version supports S3 Vectors. Test on a throwaway resource first.

variable "bedrock_kb_id" {
  type        = string
  description = "Bedrock Knowledge Base ID (set AFTER creating KB in Console). Empty string disables KB usage in Lambda."
  default     = ""
}
