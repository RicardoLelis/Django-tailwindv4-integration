# Server Provisioning Guide for Django + Tailwind Docker Setup

This guide helps you select and provision a Linux server for different traffic scenarios, from startup to enterprise scale.

## Quick Server Selection by User Scale

### 1K Daily Active Users (DAU) - Startup/MVP
**Server Specs:**
- **VPS Provider:** DigitalOcean, Linode, Vultr
- **Instance Type:** Basic droplet/instance
- **Specs:** 2 vCPU, 4GB RAM, 80GB SSD
- **Monthly Cost:** $20-40
- **Example:** DigitalOcean Droplet (4GB)

**Estimated Annual Recurring Revenue (ARR):**
- B2C SaaS ($10/month): $120K ARR
- B2B SaaS ($50/month): $600K ARR
- Enterprise ($200/month): $2.4M ARR

### 10K DAU - Growing Startup
**Server Specs:**
- **VPS Provider:** DigitalOcean, AWS, GCP
- **Instance Type:** Production-optimized
- **Specs:** 4 vCPU, 8GB RAM, 160GB SSD
- **Monthly Cost:** $80-160
- **Example:** DigitalOcean CPU-Optimized (8GB) or AWS t3.large

**Estimated ARR:**
- B2C SaaS ($10/month): $1.2M ARR
- B2B SaaS ($50/month): $6M ARR
- Enterprise ($200/month): $24M ARR

### 100K DAU - Scale-up Phase
**Server Specs:**
- **Cloud Provider:** AWS, GCP, Azure
- **Architecture:** Load-balanced setup
- **Specs:** 
  - 2-3 Web servers: c5.xlarge (4 vCPU, 8GB RAM each)
  - 1 Database: db.r5.large (2 vCPU, 16GB RAM)
  - 1 Cache server: cache.t3.medium
- **Monthly Cost:** $500-1,000
- **CDN:** CloudFlare Pro

**Estimated ARR:**
- B2C SaaS ($10/month): $12M ARR
- B2B SaaS ($50/month): $60M ARR
- Enterprise ($200/month): $240M ARR

### 1M DAU - Enterprise
**Server Specs:**
- **Cloud Provider:** AWS/GCP with multi-region
- **Architecture:** Auto-scaling, multi-AZ
- **Specs:**
  - Auto-scaling group: 5-10 c5.2xlarge instances
  - Database: RDS Multi-AZ db.r5.2xlarge
  - ElastiCache cluster
  - Load Balancer: Application Load Balancer
- **Monthly Cost:** $3,000-5,000
- **CDN:** CloudFlare Enterprise or AWS CloudFront

**Estimated ARR:**
- B2C SaaS ($10/month): $120M ARR
- B2B SaaS ($50/month): $600M ARR
- Enterprise ($200/month): $2.4B ARR

### 10M DAU - Unicorn Scale
**Server Specs:**
- **Cloud Provider:** Multi-cloud or dedicated infrastructure
- **Architecture:** Kubernetes, microservices
- **Infrastructure:**
  - Kubernetes cluster: 50+ nodes
  - Database: Aurora Global Database or similar
  - Global CDN
  - Multiple regions
- **Monthly Cost:** $50,000+
- **Requires:** Dedicated DevOps team

**Estimated ARR:**
- B2C SaaS ($10/month): $1.2B ARR
- B2B SaaS ($50/month): $6B ARR
- Enterprise ($200/month): $24B ARR

## Step-by-Step Provisioning Guide

### Step 1: Choose Your Provider

**For Beginners (1K-10K DAU):**
```bash
# Recommended: DigitalOcean
# Why: Simple, predictable pricing, great documentation
# Alternative: Linode, Vultr
```

**For Scale (100K+ DAU):**
```bash
# Recommended: AWS
# Why: Auto-scaling, managed services, global reach
# Alternative: Google Cloud, Azure
```

### Step 2: Initial Server Setup (Ubuntu 22.04 LTS)

```bash
# 1. Create server instance via provider's dashboard
# 2. SSH into your server
ssh root@your-server-ip

# 3. Create non-root user
adduser deploy
usermod -aG sudo deploy

# 4. Set up SSH key authentication
su - deploy
mkdir ~/.ssh
chmod 700 ~/.ssh
# Add your public key to ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 5. Secure SSH
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no
sudo systemctl restart ssh

# 6. Set up firewall
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Step 3: Install Docker and Docker Compose

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Logout and login again for group changes
exit
ssh deploy@your-server-ip
```

### Step 4: Deploy Application

```bash
# Clone your repository
git clone https://github.com/yourusername/your-repo.git
cd your-repo

# Set up environment variables
cp .env.prod.example .env.prod
nano .env.prod
# Edit with your production values

# Build and run
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs
```

### Step 5: SSL/TLS Setup with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Stop nginx container temporarily
docker-compose -f docker-compose.prod.yml stop nginx

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Update nginx configuration to include SSL
# Then restart nginx
docker-compose -f docker-compose.prod.yml up -d nginx
```

## Performance Optimization by Scale

### 1K-10K DAU Optimizations
```yaml
# docker-compose.prod.yml adjustments
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 3G
    environment:
      - GUNICORN_WORKERS=5
      - GUNICORN_THREADS=2
```

### 100K DAU Optimizations
```yaml
# Add Redis caching
services:
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    
  web:
    environment:
      - GUNICORN_WORKERS=9
      - GUNICORN_THREADS=4
      - DJANGO_SETTINGS_MODULE=project.settings.production
```

### 1M+ DAU Architecture Changes
- Implement database read replicas
- Use ElastiCache instead of local Redis
- Add Celery for background tasks
- Implement API rate limiting
- Use S3 for media storage
- Add APM (Application Performance Monitoring)

## Monitoring Setup

### Basic Monitoring (All Scales)
```bash
# Install monitoring stack
git clone https://github.com/stefanprodan/dockprom
cd dockprom
docker-compose up -d

# Access:
# Grafana: http://your-server:3000
# Prometheus: http://your-server:9090
```

### Advanced Monitoring (100K+ DAU)
- **APM:** NewRelic, DataDog, or Sentry
- **Uptime:** Pingdom, UptimeRobot
- **Logs:** ELK Stack or CloudWatch
- **Metrics:** Custom Grafana dashboards

## Backup Strategy by Scale

### 1K-10K DAU
```bash
# Simple daily backup script
#!/bin/bash
# Save as /home/deploy/backup.sh
BACKUP_DIR="/home/deploy/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres django_db > $BACKUP_DIR/db_$DATE.sql

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /path/to/media

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

# Add to crontab: 0 2 * * * /home/deploy/backup.sh
```

### 100K+ DAU
- Use managed database with automated backups
- Implement continuous replication
- Use object storage for media files
- Set up cross-region backup replication

## Cost Optimization Tips

### 1. Use Reserved Instances (30-70% savings)
```bash
# AWS: 1-3 year commitments
# DigitalOcean: No commitments needed
# GCP: Sustained use discounts
```

### 2. Right-sizing
- Monitor actual CPU/RAM usage
- Downsize if consistently under 50% usage
- Use auto-scaling for variable loads

### 3. CDN Usage
- Offload static content
- Reduce bandwidth costs
- Improve global performance

## Security Checklist

### Essential Security Measures
- [ ] Firewall configured (UFW/Security Groups)
- [ ] SSH key-only authentication
- [ ] Regular security updates
- [ ] HTTPS/SSL enabled
- [ ] Database backups encrypted
- [ ] Environment variables secured
- [ ] Rate limiting implemented
- [ ] DDoS protection (CloudFlare)
- [ ] Container security scanning
- [ ] Log monitoring active

## Scaling Triggers

### When to Scale Up:
- CPU consistently >70%
- RAM usage >80%
- Response time >500ms
- Database connections maxed
- Disk I/O bottlenecks

### Scaling Strategy:
1. **Vertical Scaling (1K→10K):** Upgrade server specs
2. **Horizontal Scaling (10K→100K):** Add load balancer + multiple servers
3. **Service Separation (100K→1M):** Separate database, cache, services
4. **Microservices (1M+):** Break into smaller services

## Quick Commands Reference

```bash
# Check server resources
htop
df -h
free -h

# Docker monitoring
docker stats
docker-compose -f docker-compose.prod.yml logs -f

# Database connections
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Restart services
docker-compose -f docker-compose.prod.yml restart web

# Scale web service
docker-compose -f docker-compose.prod.yml up -d --scale web=3
```

## Revenue Calculation Notes

**ARR Estimates assume:**
- 10% conversion rate from DAU to paid users
- Average B2C: $10/month
- Average B2B: $50/month  
- Average Enterprise: $200/month
- Monthly churn: 5% (B2C), 3% (B2B), 1% (Enterprise)

**Reality Check:**
- Actual conversion rates: 1-5% for B2C, 10-20% for B2B
- Pricing varies widely by market and value proposition
- Infrastructure costs typically 10-30% of revenue at scale
- Don't forget: support, development, marketing costs

## Next Steps

1. **Start Small:** Begin with 1K DAU setup
2. **Monitor Everything:** Set up monitoring early
3. **Plan for Growth:** Have scaling strategy ready
4. **Automate:** Use CI/CD as you grow
5. **Security First:** Never compromise on security
6. **Learn from Metrics:** Let data drive scaling decisions

Remember: Premature optimization is expensive. Scale when you need to, not before.