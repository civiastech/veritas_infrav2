#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root: sudo ./setup-server.sh"

log "Starting Veritas server provisioning..."

# ── 1. System update ────────────────────────────────────────────────────────
log "Updating system packages..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    curl wget git unzip ca-certificates gnupg \
    ufw fail2ban logrotate

# ── 2. Docker ───────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    log "Docker installed: $(docker --version)"
else
    log "Docker already installed: $(docker --version)"
fi

# Docker log rotation
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
systemctl restart docker

# ── 3. Deploy user ──────────────────────────────────────────────────────────
if ! id veritas &>/dev/null; then
    log "Creating veritas deploy user..."
    useradd -m -s /bin/bash veritas
else
    log "User veritas already exists"
fi

usermod -aG docker,sudo veritas

# Copy root SSH keys so the same key pair works for veritas
mkdir -p /home/veritas/.ssh
if [[ -f /root/.ssh/authorized_keys ]]; then
    cp /root/.ssh/authorized_keys /home/veritas/.ssh/authorized_keys
    chown -R veritas:veritas /home/veritas/.ssh
    chmod 700 /home/veritas/.ssh
    chmod 600 /home/veritas/.ssh/authorized_keys
fi

# Passwordless sudo required for CI/CD deploys
echo "veritas ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/veritas
chmod 440 /etc/sudoers.d/veritas

# ── 4. Swap (4 GB) ──────────────────────────────────────────────────────────
if [[ ! -f /swapfile ]]; then
    log "Creating 4 GB swap..."
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    sysctl -p
else
    log "Swap already configured"
fi

# ── 5. UFW firewall ─────────────────────────────────────────────────────────
log "Configuring UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment 'SSH'
ufw allow 80/tcp   comment 'HTTP'
ufw allow 443/tcp  comment 'HTTPS'
ufw --force enable
log "Firewall active — allowed: 22, 80, 443"

# ── 6. fail2ban ─────────────────────────────────────────────────────────────
log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
EOF
systemctl enable --now fail2ban

# ── 7. Certbot (via snap) ───────────────────────────────────────────────────
if ! command -v certbot &>/dev/null; then
    log "Installing certbot..."
    snap install --classic certbot
    ln -sf /snap/bin/certbot /usr/bin/certbot
fi
log "Certbot ready: $(certbot --version)"

# ── 8. Log rotation ─────────────────────────────────────────────────────────
cat > /etc/logrotate.d/veritas <<'EOF'
/opt/veritas/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 veritas veritas
}
EOF

# ── 9. Deployment directory ─────────────────────────────────────────────────
mkdir -p /opt/veritas
chown veritas:veritas /opt/veritas

# ── 10. Harden SSH ──────────────────────────────────────────────────────────
log "Hardening SSH config..."
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Server provisioning COMPLETE.${NC}"
echo ""
echo "  Next → switch to deploy user:"
echo "    su - veritas"
echo "  Then clone the repo:"
echo "    git clone https://github.com/civiastech/veritas_infrav2.git /opt/veritas"
