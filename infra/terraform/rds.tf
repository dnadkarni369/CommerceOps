# ---------------------------------------------------------------------------
# RDS Postgres (replaces the containerized postgres for the "cloud" deploy)
# db.t3.micro / db.t2.micro + 20GB storage is free-tier eligible for 12 months
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(var.common_tags, { Name = "${var.project_name}-db-subnet-group" })
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project_name}-postgres"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  backup_retention_period = 1

  tags = merge(var.common_tags, { Name = "${var.project_name}-postgres" })
}
