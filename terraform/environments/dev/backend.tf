terraform {
  backend "s3" {
    bucket         = "raj-kube-llm-terraform-state-benchmark"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
