# ---------------------------------------------------------------------------
# ECR repositories - one per microservice, pushed to by Jenkins
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "services" {
  for_each             = toset(var.microservices)
  name                 = "${var.project_name}/${each.value}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.common_tags, { Name = "${var.project_name}-${each.value}-ecr" })
}

resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 images to control storage cost"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}
