locals {
  name   = "kube-llm-benchmark"
  region = "us-east-1"
  tags = {
    Environment = "dev"
    Project     = "kubernetes-llm-incident-response-benchmark"
    ManagedBy   = "Terraform"
  }
}

module "vpc" {
  source = "../../modules/vpc"

  vpc_name        = "${local.name}-vpc"
  vpc_cidr        = "10.0.0.0/16"
  azs             = ["${local.region}a", "${local.region}b", "${local.region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  tags = local.tags
}

module "eks" {
  source = "../../modules/eks"

  cluster_name    = "${local.name}-cluster"
  cluster_version = "1.29"

  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnets

  node_min_size     = 1
  node_max_size     = 5
  node_desired_size = 2
  instance_types    = ["t3.medium"]

  tags = local.tags
}
