# Redis Local Installation Guide

This guide provides step-by-step instructions for installing and configuring Redis locally for the wheelchair ride-sharing application.

## Overview

Redis is used in this application for:
- **Caching**: Geocoding results, routing data, and API responses
- **Session storage**: User session management
- **Rate limiting**: API request throttling
- **Performance optimization**: Reducing database queries

## Installation by Operating System

### macOS Installation

#### Option 1: Using Homebrew (Recommended)
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify installation
redis-cli ping
# Should return: PONG
```

#### Option 2: Using MacPorts
```bash
# Install Redis via MacPorts
sudo port install redis

# Start Redis
sudo port load redis

# Test connection
redis-cli ping
```

#### Option 3: Manual Installation
```bash
# Download and compile Redis
wget https://download.redis.io/redis-stable.tar.gz
tar xzf redis-stable.tar.gz
cd redis-stable
make

# Start Redis server
src/redis-server
```

### Ubuntu/Debian Installation

#### Option 1: Using APT (Recommended)
```bash
# Update package list
sudo apt update

# Install Redis
sudo apt install redis-server

# Start Redis service
sudo systemctl start redis-server

# Enable Redis to start on boot
sudo systemctl enable redis-server

# Check status
sudo systemctl status redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

#### Option 2: Install Latest Version from Source
```bash
# Install dependencies
sudo apt update
sudo apt install build-essential tcl

# Download and compile Redis
wget https://download.redis.io/redis-stable.tar.gz
tar xzf redis-stable.tar.gz
cd redis-stable
make
make test

# Install Redis
sudo make install

# Create Redis user
sudo adduser --system --group --no-create-home redis

# Create directories
sudo mkdir /var/lib/redis
sudo chown redis:redis /var/lib/redis
sudo chmod 770 /var/lib/redis
```

### CentOS/RHEL/Fedora Installation

#### Using YUM/DNF
```bash
# For CentOS/RHEL (enable EPEL repository first)
sudo yum install epel-release
sudo yum install redis

# For Fedora
sudo dnf install redis

# Start and enable Redis
sudo systemctl start redis
sudo systemctl enable redis

# Test connection
redis-cli ping
```

### Windows Installation

#### Option 1: Using WSL (Recommended)
```bash
# Install WSL Ubuntu first, then follow Ubuntu instructions above
wsl --install -d Ubuntu
```

#### Option 2: Using Redis for Windows
```bash
# Download from: https://github.com/microsoftarchive/redis/releases
# Install the MSI package
# Start Redis from the Start menu or command line
redis-server.exe
```

#### Option 3: Using Docker
```bash
# Install Docker Desktop for Windows
# Run Redis in container
docker run --name redis-local -p 6379:6379 -d redis:7-alpine

# Test connection
docker exec -it redis-local redis-cli ping
```

## Configuration

### Basic Configuration

#### 1. Locate Redis Configuration File
```bash
# Common locations:
# macOS (Homebrew): /opt/homebrew/etc/redis.conf
# Ubuntu/Debian: /etc/redis/redis.conf
# CentOS/RHEL: /etc/redis.conf

# Find config file
find /etc -name "redis.conf" 2>/dev/null
find /opt -name "redis.conf" 2>/dev/null
```

#### 2. Basic Security Configuration
```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Key settings to modify:
# Bind to localhost only (for local development)
bind 127.0.0.1

# Set a password (optional for local development)
# requirepass your-secure-password

# Disable dangerous commands (production)
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Set max memory and eviction policy
maxmemory 256mb
maxmemory-policy allkeys-lru
```

#### 3. Performance Optimization
```bash
# Add to redis.conf for better performance
# Enable background saves
save 900 1
save 300 10
save 60 10000

# Optimize for SSD
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes

# TCP keepalive
tcp-keepalive 60
```

### Development Configuration

Create a development-specific Redis configuration:

```bash
# Create development config
sudo cp /etc/redis/redis.conf /etc/redis/redis-dev.conf

# Edit development config
sudo nano /etc/redis/redis-dev.conf
```

Development-specific settings:
```conf
# Development Redis Configuration
port 6379
bind 127.0.0.1
daemonize yes
loglevel notice
logfile /var/log/redis/redis-dev.log

# Development database settings
databases 16
save 900 1
save 300 10
save 60 10000

# Memory settings for development
maxmemory 128mb
maxmemory-policy allkeys-lru

# Disable protected mode for easier development
protected-mode no
```

## Starting Redis

### Start Redis Server

#### macOS (Homebrew)
```bash
# Start as service (persistent)
brew services start redis

# Start manually (temporary)
redis-server /opt/homebrew/etc/redis.conf

# Stop service
brew services stop redis
```

#### Ubuntu/Debian
```bash
# Start service
sudo systemctl start redis-server

# Stop service
sudo systemctl stop redis-server

# Restart service
sudo systemctl restart redis-server

# Check status
sudo systemctl status redis-server

# View logs
sudo journalctl -u redis-server
```

#### Manual Start
```bash
# Start with default config
redis-server

# Start with custom config
redis-server /path/to/redis.conf

# Start in background
redis-server --daemonize yes
```

## Testing Redis Installation

### Basic Connection Test
```bash
# Test basic connection
redis-cli ping
# Expected output: PONG

# Check Redis version
redis-cli info server | grep redis_version

# Test basic operations
redis-cli set test "Hello Redis"
redis-cli get test
redis-cli del test
```

### Test with Python (Django Context)
```python
# test_redis.py
import redis
import os

def test_redis_connection():
    try:
        # Connect to Redis
        r = redis.from_url('redis://localhost:6379/0')
        
        # Test connection
        response = r.ping()
        if response:
            print("✅ Redis connection successful")
        
        # Test basic operations
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        print(f"✅ Redis set/get test: {value.decode()}")
        
        # Test cache operations (Django style)
        r.setex('cache_test', 60, 'cached_value')  # Expire in 60 seconds
        cached = r.get('cache_test')
        print(f"✅ Redis cache test: {cached.decode()}")
        
        # Cleanup
        r.delete('test_key', 'cache_test')
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

if __name__ == "__main__":
    test_redis_connection()
```

Run the test:
```bash
python test_redis.py
```

### Test Django Cache Integration
```bash
# In your Django project directory
python manage.py shell
```

```python
# Django shell commands
from django.core.cache import cache

# Test Django cache (should use Redis)
cache.set('django_test', 'Hello from Django!', 60)
value = cache.get('django_test')
print(f"Django cache test: {value}")

# Test cache backend info
print(f"Cache backend: {cache._cache}")
```

## Monitoring Redis

### Redis CLI Monitoring
```bash
# Monitor all commands in real-time
redis-cli monitor

# Check memory usage
redis-cli info memory

# Check connected clients
redis-cli info clients

# Check stats
redis-cli info stats

# List all keys (use carefully in production)
redis-cli keys "*"

# Check database info
redis-cli info keyspace
```

### Performance Monitoring
```bash
# Check Redis performance
redis-cli --latency

# Monitor Redis operations per second
redis-cli --stat

# Check slow queries
redis-cli slowlog get 10
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Redis Server Won't Start
```bash
# Check if port 6379 is already in use
sudo lsof -i :6379

# Check Redis logs
tail -f /var/log/redis/redis-server.log

# Try starting with verbose logging
redis-server --loglevel debug
```

#### 2. Connection Refused Error
```bash
# Check if Redis is running
ps aux | grep redis

# Check Redis configuration
redis-cli ping
# If "Connection refused", Redis is not running

# Check firewall (if accessing remotely)
sudo ufw status
```

#### 3. Memory Issues
```bash
# Check Redis memory usage
redis-cli info memory

# If memory is full, clear cache
redis-cli flushdb

# Or restart Redis
sudo systemctl restart redis-server
```

#### 4. Permission Issues (Linux)
```bash
# Fix Redis directory permissions
sudo chown -R redis:redis /var/lib/redis
sudo chmod -R 755 /var/lib/redis

# Fix log file permissions
sudo chown redis:redis /var/log/redis/redis-server.log
```

#### 5. Django Can't Connect to Redis
```python
# Check Django settings
# In settings.py, verify CACHES configuration:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Test Django cache
from django.core.cache import cache
try:
    cache.set('test', 'value')
    print("Django Redis connection OK")
except Exception as e:
    print(f"Django Redis connection failed: {e}")
```

## Environment Configuration

### Create .env File
```bash
# Add to your .env file
REDIS_URL=redis://localhost:6379/0

# For password-protected Redis
# REDIS_URL=redis://:password@localhost:6379/0

# For development with multiple databases
# REDIS_URL=redis://localhost:6379/1
```

### Django Settings Update
Verify your Django settings are configured correctly:

```python
# In project/settings/base.py or settings.py
import redis
from decouple import config

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'wheelchair_rides',
        'TIMEOUT': 3600,  # 1 hour default
    }
}

# Use Redis for sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## Production Considerations

### Security
```bash
# Set password protection
redis-cli config set requirepass "your-secure-password"

# Bind to specific IP only
bind 127.0.0.1

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
```

### Backup
```bash
# Manual backup
redis-cli bgsave

# Automated backup script
#!/bin/bash
redis-cli bgsave
cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d-%H%M%S).rdb
```

### Memory Management
```bash
# Set memory limit
redis-cli config set maxmemory 256mb
redis-cli config set maxmemory-policy allkeys-lru
```

## Verification Checklist

Before proceeding with your application:

- [ ] Redis server starts successfully
- [ ] `redis-cli ping` returns PONG
- [ ] Python can connect to Redis
- [ ] Django cache is working
- [ ] Redis survives server restart (if using systemd)
- [ ] Memory usage is reasonable
- [ ] No error messages in logs

## Quick Start Commands

```bash
# Complete setup for Ubuntu/Debian
sudo apt update && sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
redis-cli ping

# Complete setup for macOS
brew install redis
brew services start redis
redis-cli ping

# Test Django integration
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'OK'); print('Redis working:', cache.get('test'))"
```

## Next Steps

After Redis is installed and running:

1. **Update your .env file** with the Redis URL
2. **Test your Django application** to ensure caching works
3. **Monitor Redis usage** during development
4. **Plan for production deployment** with appropriate security settings

Your Redis installation is now ready to support the wheelchair ride-sharing application's caching, session management, and rate limiting features.