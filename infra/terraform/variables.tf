# ============ ARCHIVO: variables.tf ============

variable "aws_region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nombre del proyecto para etiquetas"
  type        = string
  default     = "uce-tramites"
}

# --- LLAVE SSH ---
variable "ssh_key_name" {
  description = "Nombre del Key Pair existente en AWS"
  type        = string
  default     = "vockey" # Nombre oficial en tu consola
}

# --- IPs PARA ACCESO (Tus 3 ubicaciones) ---
variable "mis_ips_ipv4" {
  description = "Lista de IPs IPv4 (Tus dos casas)"
  type        = list(string)
  default     = [
    "190.242.106.93/32", # Casa 1
    "200.50.232.234/32"  # Casa 2
  ]
}

variable "mi_celular_ipv6" {
  description = "IP IPv6 de tu celular"
  type        = list(string)
  default     = ["2800:430:b208:ea33:49fd:18c6:9b68:fdeb/128"]
}

# --- CONFIGURACIÓN DE RED ---
variable "vpc_cidr" { default = "10.0.0.0/16" }
variable "public_subnet_cidr" { default = "10.0.1.0/24" }
variable "private_subnet_cidr" { default = "10.0.2.0/24" }

# --- TIPOS DE INSTANCIA ---
variable "instance_type_bastion" { default = "t2.micro" }
variable "instance_type_apps"    { default = "t2.medium" }
variable "instance_type_infra"   { default = "t2.medium" }
