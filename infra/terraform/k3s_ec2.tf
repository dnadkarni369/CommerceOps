# ---------------------------------------------------------------------------
# Single EC2 instance dedicated to running k3s (the ASG in alb_asg.tf is for
# the alternate docker-compose deployment path - k3s runs better as a fixed,
# addressable single node than behind an Auto Scaling Group, and a single
# t3.micro is all the free tier gives you room for anyway).
# ---------------------------------------------------------------------------

resource "aws_security_group" "k3s" {
  name        = "${var.project_name}-k3s-sg"
  description = "k3s API, app ingress, and SSH for Ansible/Jenkins"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP (Traefik ingress)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "k3s Kubernetes API"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # tighten to your Jenkins/office IP in real use
  }

  ingress {
    description = "SSH (restrict to your IP in production)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "NodePort range (only needed if bypassing the Ingress)"
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, { Name = "${var.project_name}-k3s-sg" })
}

resource "aws_instance" "k3s_node" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type # t3.micro - free tier
  subnet_id              = aws_subnet.public[0].id
  key_name               = var.key_pair_name != "" ? var.key_pair_name : null
  vpc_security_group_ids = [aws_security_group.k3s.id]

  root_block_device {
    volume_size = 20 # stays within the 30GB free-tier EBS allowance
    volume_type = "gp3"
  }

  tags = merge(var.common_tags, { Name = "${var.project_name}-k3s-node" })
}

# Elastic IP so the node's address survives a stop/start (EIP is free while
# attached to a running instance - only billed if left unattached)
resource "aws_eip" "k3s_node" {
  instance = aws_instance.k3s_node.id
  domain   = "vpc"
  tags     = merge(var.common_tags, { Name = "${var.project_name}-k3s-eip" })
}
