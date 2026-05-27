output "api_url" {
  value       = aws_apigatewayv2_api.http.api_endpoint
  description = "Backend API endpoint (also reachable via /api/* on CloudFront)"
}

output "cloudfront_url" {
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
  description = "Public HTTPS URL — give this to trainer"
}

output "docs_bucket" {
  value       = aws_s3_bucket.docs.id
  description = "S3 bucket for uploaded documents (use as Bedrock KB data source)"
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.id
}

output "userstore_table" {
  value = aws_dynamodb_table.userstore.name
}

output "lambda_role_arn" {
  value       = aws_iam_role.lambda.arn
  description = "Add this principal to your Bedrock KB role trust if KB needs to call back to your account"
}
