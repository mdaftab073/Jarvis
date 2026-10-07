# Jarvis — AWS EC2 Step-by-Step Production Deployment Playbook

This guide walks you through deploying Jarvis onto a single **Ubuntu AWS EC2 instance** using Docker Compose and Nginx with free SSL (Let's Encrypt).

---

## Architecture Overview

```
Internet (User) 
   │
   ▼ HTTPS :443 / HTTP :80
[ Nginx Reverse Proxy on EC2 ]
   ├── /          ──> Serves Static Frontend (/var/www/jarvis/frontend/dist)
   └── /api/      ──> Proxies to FastAPI Backend (127.0.0.1:8000)
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
         [ jarvis-api ]            [ jarvis-worker ]
               │                         │
               ├─────────────────────────┤
               ▼                         ▼
         [ PostgreSQL 16 ]         [ ChromaDB ]
```

---

## Phase 1: Launch the AWS EC2 Instance

1. Log into your [AWS Management Console](https://console.aws.amazon.com/ec2).
2. Go to **EC2** > **Instances** > click **Launch Instances**.
3. **Name**: `jarvis-production`
4. **Application and OS Images (AMI)**: **Ubuntu Server 24.04 LTS** (or 22.04 LTS), 64-bit (x86).
5. **Instance Type**:
   * Recommended: **`t3.medium`** (2 vCPU, 4 GiB RAM) for smooth PyTorch embedding processing.
   * Budget alternative: **`t3.small`** (2 vCPU, 2 GiB RAM) — our setup script configures a 4 GB swap file so this works comfortably without out-of-memory errors.
6. **Key Pair (login)**:
   * Select an existing `.pem` key pair or click **Create new key pair** (e.g. `jarvis-key.pem`).
   * Download and save it securely (e.g., in `~/.ssh/`).
7. **Network Settings (Security Group)**:
   * Check **Allow SSH traffic from Anywhere** (or your specific IP).
   * Check **Allow HTTP traffic from the internet** (port 80).
   * Check **Allow HTTPS traffic from the internet** (port 443).
8. **Configure Storage**:
   * Set **30 GiB** (gp3) root volume (sufficient for Docker images, dependencies, and HuggingFace cache).
9. Click **Launch Instance**.

---

## Phase 2: Allocate & Associate an Elastic IP

An Elastic IP ensures your server IP never changes when rebooted:
1. In the EC2 console left menu, go to **Network & Security** > **Elastic IPs**.
2. Click **Allocate Elastic IP address** > **Allocate**.
3. Select the newly created IP > click **Actions** > **Associate Elastic IP address**.
4. Choose your `jarvis-production` instance and click **Associate**.
5. Note this Public IP (referred to below as `<YOUR_EC2_IP>`).

---

## Phase 3: Connect via SSH & Initialize the Server

### 1. Connect to the Instance
On your local machine (PowerShell, Terminal, or WSL):
```bash
ssh -i /path/to/jarvis-key.pem ubuntu@<YOUR_EC2_IP>
```

### 2. Run the Initialization Script
Once connected, download and run the setup script to install Docker, Compose, Nginx, Node.js, and configure 4GB swap space:
```bash
curl -fsSL https://raw.githubusercontent.com/mdaftab073/Jarvis/main/docs/deployment/setup_server.sh -o setup_server.sh || nano setup_server.sh
chmod +x setup_server.sh
sudo ./setup_server.sh
```

Log out and back in once so the `docker` group takes effect:
```bash
exit
```
Reconnect:
```bash
ssh -i /path/to/jarvis-key.pem ubuntu@<YOUR_EC2_IP>
```

---

## Phase 4: Clone the Codebase & Configure Environment

### 1. Clone into `/var/www/jarvis`
```bash
sudo mkdir -p /var/www/jarvis
sudo chown -R ubuntu:ubuntu /var/www/jarvis
git clone https://github.com/mdaftab073/Jarvis.git /var/www/jarvis
cd /var/www/jarvis
```

### 2. Create the Production `.env` File
```bash
cp .env.example .env
nano .env
```
Fill in your production values:
```ini
POSTGRES_DB=jarvis
POSTGRES_USER=jarvis
POSTGRES_PASSWORD=your_secure_postgres_password_here

GROQ_API_KEY=gsk_your_groq_api_key_here

JARVIS_PORT=8000

# Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CONNECTOR_ENCRYPTION_KEY=your_generated_fernet_key_here

# Generate with: openssl rand -hex 16
METRICS_ADMIN_TOKEN=your_secure_metrics_token_here

# Your Google OAuth Client ID
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com

# Generate with: openssl rand -hex 32
JWT_SECRET_KEY=your_secure_jwt_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Production domain (or http://<YOUR_EC2_IP> if testing before domain setup)
ALLOWED_ORIGINS=https://yourdomain.com,http://<YOUR_EC2_IP>
```
Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## Phase 5: Start the Backend Stack (Docker Compose)

```bash
cd /var/www/jarvis

# 1. Verify Compose syntax
docker compose config

# 2. Build and launch all 4 services (postgres, chroma, jarvis-api, worker)
docker compose up -d --build

# 3. Verify all containers are healthy
docker compose ps
```
You should see:
* `jarvis-postgres-1` (healthy)
* `jarvis-chroma-1` (healthy)
* `jarvis-jarvis-api-1` (healthy)
* `jarvis-worker-1` (running)

Test the backend health locally:
```bash
curl http://localhost:8000/system/health
```
*(Should return `{"success": true, "data": {"overall": "healthy", ...}}`)*

---

## Phase 6: Build the Frontend

```bash
cd /var/www/jarvis/frontend

# Configure frontend environment
cat << 'EOF' > .env
# For same-domain Nginx reverse proxy, leave empty or set to /api
VITE_API_BASE_URL=
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
EOF

# Install dependencies and build static bundle
npm install
npm run build
```
Verify that the `dist/` folder was generated:
```bash
ls -la /var/www/jarvis/frontend/dist
```

---

## Phase 7: Configure Nginx Reverse Proxy

### 1. Copy the Nginx Configuration
```bash
sudo cp /var/www/jarvis/docs/deployment/nginx.conf /etc/nginx/sites-available/jarvis
sudo nano /etc/nginx/sites-available/jarvis
```
Replace `YOUR_DOMAIN_OR_IP` with your actual domain (e.g. `jarvis.yourdomain.com`) or your EC2 Public IP (`<YOUR_EC2_IP>`).

### 2. Enable the Site & Restart Nginx
```bash
# Enable the site
sudo ln -sf /etc/nginx/sites-available/jarvis /etc/nginx/sites-enabled/jarvis

# Disable the default welcome page
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx syntax
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

Now, visit `http://<YOUR_EC2_IP>` in your browser. Your frontend UI should load and interact with the backend API!

---

## Phase 8: Domain DNS & SSL Certificate (Let's Encrypt)

### 1. Point Your Domain to EC2
Go to your DNS provider (Namecheap, GoDaddy, Cloudflare, Route53, etc.):
* Create an **A record**:
  * Host: `@` or `jarvis` (subdomain)
  * Value: `<YOUR_EC2_IP>`
  * TTL: 300 seconds

### 2. Obtain Free SSL Certificate
Once your DNS propagates (usually 2–5 minutes):
```bash
sudo certbot --nginx -d yourdomain.com
```
* Enter your email.
* Agree to Terms of Service.
* Certbot will automatically configure SSL in `/etc/nginx/sites-available/jarvis` and set up auto-renewal.

---

## Phase 9: Google Cloud Console Configuration

To allow students to log in via Google OAuth on production:
1. Go to the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
2. Select your OAuth 2.0 Web Client ID.
3. Under **Authorized JavaScript origins**, add:
   * `https://yourdomain.com` (and `http://<YOUR_EC2_IP>` if testing without domain)
4. Under **Authorized redirect URIs**, add:
   * `https://yourdomain.com`
5. Click **Save**.

---

## Phase 10: Maintenance & Operations Cheat Sheet

### View Logs
```bash
# API container logs
docker compose -f /var/www/jarvis/docker-compose.yml logs -f --tail 100 jarvis-api

# Worker container logs
docker compose -f /var/www/jarvis/docker-compose.yml logs -f --tail 100 worker

# Nginx access & error logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Deploy Code Updates
```bash
cd /var/www/jarvis
git pull origin main

# Rebuild backend if Python code changed
docker compose up -d --build jarvis-api worker

# Rebuild frontend if React code changed
cd frontend && npm install && npm run build
```

### Automated Reboots
All Docker containers have `restart: unless-stopped`, and Nginx is managed by `systemd`. If the EC2 instance is rebooted, all services will automatically resume without manual intervention.
