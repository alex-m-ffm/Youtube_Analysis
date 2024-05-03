variable "reports" {
  type = list(string)
}

resource "aws_dynamodb_table" "report_tables" {
  count = length(var.reports)

  name = var.reports[count.index]
  billing_mode = "PAY_PER_REQUEST"
  
  hash_key = "composite_key"
  range_key = "createTime"

  attribute {
    name = "composite_key"
    type = "S"
  }

  attribute {
    name = "createTime"
    type = "S"
  }
}

resource "aws_dynamodb_table" "jobs_table" {

  name = "reports"
  billing_mode = "PAY_PER_REQUEST"
  
  hash_key = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

output "table_arns" {
  value = concat([for i in range(length(var.reports)) : aws_dynamodb_table.report_tables[i].arn], [aws_dynamodb_table.jobs_table.arn])
}

# now for the mapping tables

variable "mappings" {
  type = list(string)
  default = ["traffic_source_type", "playback_location_type", "traffic_source_detail", 
  "device_type", "operating_system", "sharing_service", "annotations_type"]
}

resource "aws_dynamodb_table" "mapping_tables" {
  count = length(var.mappings)

  name = var.mappings[count.index]
  billing_mode = "PAY_PER_REQUEST"
  
  hash_key = "id"

  attribute {
    name = "id"
    type = "N"
  }
}
