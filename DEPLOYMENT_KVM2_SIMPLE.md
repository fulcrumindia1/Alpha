# FULCRUM CLUSTER A — SIMPLE PRODUCTION DEPLOYMENT GUIDE (KVM 2)

**Architecture Philosophy: The Mental-Peace Stack**
- **Zero Complex Orchestration**: No Dokploy, no Traefik, no Kubernetes, no Redis, no Celery, no FastAPI.
- **2 Disposable Containers**: **Caddy** (automatic HTTPS/Let's Encrypt reverse proxy) + **Fulcrum** (Streamlit on internal port 8501).
- **1 Permanent Data Store**: **Supabase Cloud** (PostgreSQL 15+ & GoTrue Auth).
- **Production Server IP**: `187.126.114.81` (Hostinger KVM 2)
- **Domain**: `fulcrumindia.online` | **App Portal**: `app.fulcrumindia.online`
- **Single-Command Operating Model**:
  ```bash
  ssh root@187.126.114.81
  cd /opt/fulcrum
  ./scripts/deploy.sh
  ```

---

## 1. Architecture Diagram

```text
                             INTERNET
                                │
                    fulcrumindia.online (ports 80 / 443)
                    app.fulcrumindia.online
                                │
                                ▼
                              CADDY
                    HTTPS + Automatic Let's Encrypt
                                │  (internal docker network: fulcrum-net)
                                ▼
                       ┌────────────────┐
                       │  Docker (Host) │
                       │                │
                       │   Fulcrum      │
                       │   Streamlit    │
                       │     :8501      │
                       └───────┬────────┘
                               │
                               ▼
                            SUPABASE
                        Auth + PostgreSQL
```

* `app.fulcrumindia.online` points to this VPS (`187.126.114.81`).
* `fulcrumindia.online` & `www.fulcrumindia.online` point to Vercel (marketing landing page) and are NOT managed by Caddy.
* Streamlit port `8501` is strictly internal to Docker network `fulcrum-net` (no host ports published) — NEVER exposed to the host or public Internet.
* Caddy automatically provisions, configures, and renews Let's Encrypt SSL certificates for `app.fulcrumindia.online`.

---

## 2. First-Time Hostinger KVM 2 Setup

### Step A: Initial Server Update
SSH into your server:
```bash
ssh root@187.126.114.81
sudo apt update && sudo apt upgrade -y
```

### Step B: Install Docker & Docker Compose
Install official Docker Engine:
```bash
sudo apt install -y curl ca-certificates git ufw
curl -fsSL https://get.docker.com | sudo sh

# Allow current user to run Docker
sudo usermod -aG docker $USER
newgrp docker
```
Verify Docker:
```bash
docker --version
docker compose version
```

### Step C: Configure Firewall (UFW)
Expose strictly the 3 required ports:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Let's Encrypt challenge & redirect)
sudo ufw allow 443/tcp   # HTTPS (Production Traffic)
sudo ufw enable
```
*(Verify port 8501 is NOT listed in `sudo ufw status`)*.

---

## 3. Application Setup

### Step D: Clone Repository
```bash
sudo mkdir -p /opt/fulcrum
sudo chown -R $USER:$USER /opt/fulcrum
git clone https://github.com/fulcrumindia1/Alpha.git /opt/fulcrum
cd /opt/fulcrum
chmod +x scripts/*.sh
```

### Step E: Configure Environment Secrets (.env)
Create `/opt/fulcrum/.env` (this file is `.gitignore`d and never committed to Git):
```bash
nano /opt/fulcrum/.env
```
Paste your production secrets:
```ini
DATA_BACKEND=supabase
SUPABASE_URL=https://<YOUR-PROJECT-ID>.supabase.co
SUPABASE_PUBLISHABLE_KEY=eyJhbGciOi...
SUPABASE_SECRET_KEY=eyJhbGciOi...

# Production Domain Configuration
DOMAIN=app.fulcrumindia.online
```

### Step F: Configure DNS Records (Hostinger / Domain Registrar)
In your domain registrar DNS settings for **`fulcrumindia.online`**, add these 3 records:

| Record Type | Host / Name | Points to (Value) | TTL | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `app` | `187.126.114.81` | 300 / Auto | App Portal -> Hostinger VPS (Fulcrum + Caddy) |
| **A** / **CNAME** | `@` / `www` | *Vercel IP / CNAME* | 300 / Auto | Landing Page -> Vercel (Marketing Site) |

---

## 4. Launching the Application

### Step G: Run the One-Command Deployment
```bash
./scripts/deploy.sh
```

The script will automatically:
1. Pull latest code from Git (`main` branch).
2. Validate `.env` and Supabase configuration.
3. Build the Docker image.
4. Launch `fulcrum-app` and `fulcrum-caddy`.
5. Wait for the Streamlit health check to pass.
6. Verify live Supabase database connectivity.
7. Print the running container status.

### Step H: Verify Live HTTPS
Open your browser and navigate to:
```text
https://app.fulcrumindia.online
```
* Caddy automatically provisions the SSL certificate from Let's Encrypt in seconds.
* Streamlit WebSocket connects cleanly over WSS with no manual reverse-proxy tuning required.

---

## 5. Day-to-Day Operations Manual

Everyday management is handled with simple, single-purpose scripts in `/opt/fulcrum`:

| Operation | Command | Description |
| :--- | :--- | :--- |
| **Deploy New Version** | `./scripts/deploy.sh` | Pulls Git, builds, restarts containers, runs healthcheck |
| **Check System Status** | `./scripts/status.sh` | Shows container states, uptime, memory, and CPU usage |
| **Inspect Application Logs** | `./scripts/logs.sh` | Tails live Streamlit logs (Ctrl+C to exit) |
| **Inspect Caddy Logs** | `./scripts/logs.sh caddy` | Tails live HTTPS and proxy logs |
| **Safe Restart** | `./scripts/restart.sh` | Restarts containers with zero data loss |
| **Emergency Rollback** | `./scripts/rollback.sh` | Reverts to previous Git commit and rebuilds in <5 minutes |

---

## 6. How to Rollback in Under 5 Minutes

If a bad commit or regression is released:
```bash
cd /opt/fulcrum

# Revert to the immediately preceding Git commit:
./scripts/rollback.sh

# Or revert to a specific known-good commit:
./scripts/rollback.sh abc1234
```
**Why Rollbacks Are 100% Safe:**
- The Docker containers are disposable stateless workers.
- All persistent production data (users, auth, profiles, journeys, schemes, consultations) lives exclusively in Supabase Cloud.
- Destroying or rolling back the container **never deletes or modifies database records**.

---

## 7. Emergency Recovery Procedure

If the application is ever unresponsive:

```text
Step 1: SSH into server
        ssh pravin@YOUR_SERVER_IP
        cd /opt/fulcrum

Step 2: Check container states
        ./scripts/status.sh

Step 3: Check recent error logs
        ./scripts/logs.sh

Step 4: Simple restart
        ./scripts/restart.sh

Step 5: If still unresponsive, rebuild container stack
        docker compose down
        docker compose up -d --build

Step 6: If the new code itself is broken, rollback
        ./scripts/rollback.sh
```

---

## 8. Server Reboot Recovery

Both `fulcrum` and `caddy` are configured with `restart: unless-stopped`:
* If the KVM 2 server reboots (e.g. Hostinger maintenance or kernel update), Docker automatically starts both Caddy and Fulcrum on boot.
* No manual SSH or intervention is required.
