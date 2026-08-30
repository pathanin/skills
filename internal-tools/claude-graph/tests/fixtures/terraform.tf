resource "aws_instance" "relay" {
  ami = "ami-123"
}
variable "region" {
  type = string
}
module "network" {
  source = "./net"
}
output "relay_ip" {
  value = "1.2.3.4"
}
