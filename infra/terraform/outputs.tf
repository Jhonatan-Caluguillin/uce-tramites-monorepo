output "bastion_public_ip" {
  value = aws_instance.bastion.public_ip
}

output "apps_public_ip" {
  value = aws_instance.apps.public_ip
}

output "apps_private_ip" {
  value = aws_instance.apps.private_ip
}

output "infra_private_ip" {
  value = aws_instance.infra.private_ip
}
