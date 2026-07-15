terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Uncomment and configure once you have an S3 bucket + DynamoDB table for
  # remote state locking (recommended for anything beyond solo/demo use):
  #
  # backend "s3" {
  #   bucket         = "commerceops-terraform-state"
  #   key            = "commerceops/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "commerceops-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}
