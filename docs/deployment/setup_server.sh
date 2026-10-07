#!/usr/bin/env bash
# ==============================================================================
# Jarvis — Automated EC2 Setup Script (Ubuntu 22.04 / 24.04 LTS)
# Run as root or with sudo:
#   chmod +x setup_server.sh && sudo ./setup_server.sh
# ==============================================================================

set -euo pipefail

echo "=================================================="
echo " 1. Updating System Packages"
echo "=================================================="
apt-get update -y && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg lsb-release git nginx certbot python3-certbot-nginx

echo "=================================================="
echo " 2. Setting Up 4GB Swap Space"
echo "=================================================="
# Crucial for PyTorch / ML inference on smaller EC2 instances (e.g. t3.small)
if [ ! -f /swapfile ]; then
    echo "Creating 4GB swapfile..."
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "Swap created successfully."
else
    echo "Swapfile already exists. Skipping."
fi

echo "=================================================="
echo " 3. Installing Docker & Docker Compose Plugin"
echo "=================================================="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# Add ubuntu user to docker group if present
if id "ubuntu" &>/dev/null; then
    usermod -aG docker ubuntu
fi

echo "=================================================="
echo " 4. Installing Node.js 20 LTS (for Frontend Build)"
echo "=================================================="
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "=================================================="
echo " Setup Completed Successfully!"
echo " Docker: $(docker --version)"
echo " Compose: $(docker compose version)"
echo " Node: $(node -v)"
echo " Nginx: $(nginx -v 2>&1)"
echo " Swap: $(free -h | grep -i swap)"
echo "=================================================="
