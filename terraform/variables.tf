variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "project" {
  type    = string
  default = "xops-study"
}

variable "team" {
  type        = string
  description = "Team identifier, e.g. G3"
}

variable "owner" {
  type        = string
  description = "Your name/handle, lowercase no spaces"
}

variable "bedrock_model_id" {
  type    = string
  default = "anthropic.claude-3-5-haiku-20241022-v1:0"
}

variable "embedding_model_id" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}

variable "lambda_zip_path" {
  type        = string
  description = "Path to packaged Lambda zip (run scripts/build.ps1 first). Relative to terraform/ dir."
  default     = "../build/lambda.zip"
}
