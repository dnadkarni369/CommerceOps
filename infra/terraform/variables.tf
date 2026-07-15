variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
  default     = "commerceops"
}

variable "environment" {
  description = "Deployment environment tag"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "availability_zones" {
  description = "AZs to spread subnets across"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

# Free-tier friendly defaults. t2.micro / t3.micro give 750 free hours/month
# for the first 12 months - keep instance count low and destroy when idle.
variable "instance_type" {
  description = "EC2 instance type for the app Auto Scaling Group"
  type        = string
  default     = "t3.micro"
}

variable "asg_min_size" {
  type    = number
  default = 1
}

variable "asg_max_size" {
  type    = number
  default = 2
}

variable "asg_desired_capacity" {
  type    = number
  default = 1
}

variable "db_instance_class" {
  description = "RDS instance class - db.t3.micro/db.t2.micro are free-tier eligible"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  type    = string
  default = "commerceops"
}

variable "db_username" {
  type    = string
  default = "commerceops"
}

variable "db_password" {
  description = "RDS master password. Pass via TF_VAR_db_password or a tfvars file that is gitignored - never commit this."
  type        = string
  sensitive   = true
}

variable "key_pair_name" {
  description = "Existing EC2 key pair name for SSH access (used by Ansible)"
  type        = string
  default     = ""
}

variable "microservices" {
  description = "List of microservices that get their own ECR repository"
  type        = list(string)
  default = [
    "frontend",
    "api-service",
    "auth-service",
    "order-service",
    "ai-recommendation-service",
    "worker-service",
  ]
}

variable "common_tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    Project   = "commerceops"
    ManagedBy = "terraform"
  }
}
