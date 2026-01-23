# ============ Locals y Data Sources ============
locals {
  tags = {
    Project = var.project_name
    Env     = "qa"
  }
  user_data_common = <<-EOT
    #!/bin/bash
    apt-get update -y
    apt-get install -y docker.io git
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
  EOT
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# ============ VPC e Internet Gateway ============
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.tags, { Name = "${var.project_name}-vpc" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${var.project_name}-igw" })
}

# ============ Subredes ============
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"
  tags                    = merge(local.tags, { Name = "${var.project_name}-public" })
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidr
  availability_zone = "${var.aws_region}a"
  tags              = merge(local.tags, { Name = "${var.project_name}-private" })
}

# ============ NAT GATEWAY ============
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(local.tags, { Name = "${var.project_name}-nat-eip" })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
  tags          = merge(local.tags, { Name = "${var.project_name}-nat-gateway" })
  depends_on    = [aws_internet_gateway.igw]
}

# ============ Tablas de Rutas ============
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${var.project_name}-rt-public" })
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${var.project_name}-rt-private" })
}

resource "aws_route" "private_nat_route" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}

resource "aws_route_table_association" "private_assoc" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

# ============ Security Groups ============

# BASTION: Acceso desde tus IPs por 443 y respaldo por 22
resource "aws_security_group" "bastion" {
  name        = "${var.project_name}-sg-bastion"
  description = "Acceso seguro desde multiples ubicaciones"
  vpc_id      = aws_vpc.this.id

  ingress {
    description      = "Acceso seguro 443"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    # AQUÍ USAMOS LAS LISTAS DE VARIABLES:
    cidr_blocks      = var.mis_ips_ipv4
    ipv6_cidr_blocks = var.mi_celular_ipv6
  }

  ingress {
    description = "Respaldo EC2 Connect"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Esto evita el error de "Failed to connect"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# APPS: Abierto al mundo por el 80, SSH solo desde Bastion
resource "aws_security_group" "apps" {
  name   = "${var.project_name}-sg-apps"
  vpc_id = aws_vpc.this.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# INFRA: Solo accesible desde la red interna
resource "aws_security_group" "infra" {
  name   = "${var.project_name}-sg-infra"
  vpc_id = aws_vpc.this.id

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  ingress {
    description     = "DB and Messaging ports"
    from_port       = 5432 # Postgres
    to_port         = 27017 # Rango hasta Mongo para simplificar
    protocol        = "tcp"
    security_groups = [aws_security_group.apps.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ============ Instancias EC2 ============

resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_bastion
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  key_name                    = var.ssh_key_name
  associate_public_ip_address = true
  user_data                   = local.user_data_common
  tags                        = merge(local.tags, { Name = "${var.project_name}-bastion" })
}

resource "aws_instance" "apps" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type_apps
  subnet_id              = aws_subnet.private.id
  vpc_security_group_ids = [aws_security_group.apps.id]
  key_name               = var.ssh_key_name
  user_data              = local.user_data_common
  tags                   = merge(local.tags, { Name = "${var.project_name}-apps" })
}

resource "aws_instance" "infra" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type_infra
  subnet_id              = aws_subnet.private.id
  vpc_security_group_ids = [aws_security_group.infra.id]
  key_name               = var.ssh_key_name
  user_data              = local.user_data_common
  tags                   = merge(local.tags, { Name = "${var.project_name}-infra" })
}