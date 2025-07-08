
# KG-System Enterprise SaaS Infrastructure
# Based on proven Sweet Spot: High Performance Enterprise Mode

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "kg-system-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "KG-System-Enterprise"
      Environment = var.environment
      SweetSpot   = "HighPerformanceEnterpriseMode"
      ManagedBy   = "Terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "Primary AWS region"
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  default     = "production"
}

variable "sweet_spot_performance_target" {
  description = "Target performance based on Sweet Spot analysis"
  default     = "0.70s"
}

# VPC Configuration for Enterprise Deployment
resource "aws_vpc" "kg_system_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "kg-system-enterprise-vpc"
    Tier = "Enterprise"
  }
}

# Public Subnets for Load Balancers
resource "aws_subnet" "public_subnets" {
  count             = 3
  vpc_id            = aws_vpc.kg_system_vpc.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  map_public_ip_on_launch = true

  tags = {
    Name = "kg-system-public-subnet-${count.index + 1}"
    Type = "Public"
  }
}

# Private Subnets for Application Tier
resource "aws_subnet" "private_subnets" {
  count             = 3
  vpc_id            = aws_vpc.kg_system_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "kg-system-private-subnet-${count.index + 1}"
    Type = "Private"
    Tier = "Application"
  }
}

# Database Subnets
resource "aws_subnet" "database_subnets" {
  count             = 3
  vpc_id            = aws_vpc.kg_system_vpc.id
  cidr_block        = "10.0.${count.index + 20}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "kg-system-db-subnet-${count.index + 1}"
    Type = "Database"
    Tier = "Data"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "kg_system_igw" {
  vpc_id = aws_vpc.kg_system_vpc.id

  tags = {
    Name = "kg-system-internet-gateway"
  }
}

# EKS Cluster for Sweet Spot Application
resource "aws_eks_cluster" "kg_system_cluster" {
  name     = "kg-system-enterprise"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.28"

  vpc_config {
    subnet_ids              = concat(aws_subnet.public_subnets[*].id, aws_subnet.private_subnets[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = {
    Name        = "kg-system-enterprise-cluster"
    SweetSpot   = "HighPerformanceMode"
    Performance = var.sweet_spot_performance_target
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

# RDS PostgreSQL for Enterprise Data
resource "aws_db_instance" "kg_system_db" {
  identifier = "kg-system-enterprise-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"
  
  allocated_storage     = 1000
  max_allocated_storage = 10000
  storage_type          = "gp3"
  storage_encrypted     = true
  
  db_name  = "kgsystem"
  username = "kgadmin"
  password = var.db_password
  port     = 5432
  
  multi_az               = true
  publicly_accessible    = false
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  db_subnet_group_name   = aws_db_subnet_group.kg_system_db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.database_sg.id]
  
  performance_insights_enabled = true
  monitoring_interval         = 60
  monitoring_role_arn         = aws_iam_role.rds_enhanced_monitoring.arn
  
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "kg-system-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Name         = "kg-system-enterprise-database"
    Environment  = var.environment
    SweetSpot    = "HighPerformanceData"
    MultiTenant  = "true"
  }
}

# ElastiCache Redis for Sweet Spot Performance Caching
resource "aws_elasticache_replication_group" "kg_system_redis" {
  replication_group_id       = "kg-system-enterprise"
  description                = "Redis cluster for KG-System Sweet Spot performance"
  
  port                = 6379
  parameter_group_name = "default.redis7"
  engine_version      = "7.0"
  node_type          = "cache.r6g.large"
  
  num_cache_clusters = 3
  
  subnet_group_name  = aws_elasticache_subnet_group.kg_system_redis_subnet_group.name
  security_group_ids = [aws_security_group.redis_sg.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
  
  tags = {
    Name        = "kg-system-enterprise-cache"
    SweetSpot   = "PerformanceOptimized"
    Performance = "SubSecondResponse"
  }
}

# Application Load Balancer
resource "aws_lb" "kg_system_alb" {
  name               = "kg-system-enterprise-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets           = aws_subnet.public_subnets[*].id

  enable_deletion_protection = true
  enable_http2              = true

  tags = {
    Name      = "kg-system-enterprise-alb"
    SweetSpot = "HighAvailability"
  }
}

# CloudFront Distribution for Global Performance
resource "aws_cloudfront_distribution" "kg_system_cdn" {
  origin {
    domain_name = aws_lb.kg_system_alb.dns_name
    origin_id   = "kg-system-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "KG-System Enterprise CDN for global Sweet Spot performance"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "kg-system-alb"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "CloudFront-Forwarded-Proto"]
      
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress              = true
  }

  price_class = "PriceClass_All"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name        = "kg-system-enterprise-cdn"
    SweetSpot   = "GlobalPerformance"
    Performance = "EdgeOptimized"
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

# Outputs
output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.kg_system_cluster.endpoint
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.kg_system_db.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.kg_system_redis.primary_endpoint_address
}

output "load_balancer_dns" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.kg_system_alb.dns_name
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.kg_system_cdn.domain_name
}
