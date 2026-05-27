# Single-table design (matches src/adapters/userstore.py DynamoDBUserStore).
# PK=user_id, SK=DOC#<doc_id> or QUERY#<timestamp>
resource "aws_dynamodb_table" "userstore" {
  name         = "${local.name_prefix}-userstore"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "sk"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }
}
