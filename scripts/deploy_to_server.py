"""
scripts/deploy_to_server.py
===========================
Packages Fulcrum Cluster A, transfers to the remote host (pravin@10.59.191.57),
builds and starts the Docker container, and runs all verification test suites.
"""

import os
import sys
import tarfile
import subprocess
import toml

REMOTE_HOST = "pravin@10.59.191.57"
REMOTE_DIR = "/home/pravin/fulcrum-cluster-a"
ARCHIVE_NAME = "fulcrum_deploy.tar.gz"


def create_env_file():
    """Generates .env from .streamlit/secrets.toml for Docker Compose."""
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if not os.path.exists(secrets_path):
        print("[-] Error: .streamlit/secrets.toml not found!")
        sys.exit(1)
        
    with open(secrets_path, "r", encoding="utf-8") as f:
        secrets = toml.load(f)
        
    url = secrets.get("SUPABASE_URL", "")
    pub_key = secrets.get("SUPABASE_PUBLISHABLE_KEY") or secrets.get("SUPABASE_ANON_KEY", "")
    sec_key = secrets.get("SUPABASE_SECRET_KEY") or secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(f"DATA_BACKEND=supabase\n")
        f.write(f"SUPABASE_URL={url}\n")
        f.write(f"SUPABASE_PUBLISHABLE_KEY={pub_key}\n")
        f.write(f"SUPABASE_SECRET_KEY={sec_key}\n")
        f.write(f"DOMAIN=:80\n")
    print("[+] Generated .env file from secrets.toml")


def create_deployment_archive():
    """Packages all necessary files into a compressed tarball."""
    print(f"[*] Packaging deployment archive: {ARCHIVE_NAME}...")
    
    files_to_pack = [
        "Dockerfile",
        ".dockerignore",
        "docker-compose.yml",
        "Caddyfile",
        "requirements.txt",
        "supabase_setup.sql",
        "DEPLOYMENT_KVM2_SIMPLE.md",
        ".env",
        "app.py"
    ]
    
    dirs_to_pack = [
        ".streamlit",
        "components",
        "services",
        "views",
        "scripts",
        "tests"
    ]
    
    def filter_tar(tarinfo):
        # Exclude pycache, database files, backups, pdfs
        name = tarinfo.name
        if "__pycache__" in name or name.endswith(".pyc") or name.endswith(".db"):
            return None
        if "backups" in name or "scratch" in name or name.endswith(".pdf"):
            return None
        return tarinfo

    with tarfile.open(ARCHIVE_NAME, "w:gz") as tar:
        for f in files_to_pack:
            if os.path.exists(f):
                tar.add(f, arcname=f)
        for d in dirs_to_pack:
            if os.path.exists(d):
                tar.add(d, arcname=d, filter=filter_tar)
                
    size_mb = os.path.getsize(ARCHIVE_NAME) / (1024 * 1024)
    print(f"[+] Archive created successfully: {ARCHIVE_NAME} ({size_mb:.2f} MB)")


def run_ssh_command(cmd: str, check=True):
    """Executes a command on the remote host via OpenSSH."""
    print(f"\n[SSH >>>] {cmd}")
    res = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", REMOTE_HOST, cmd],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if res.stdout:
        safe_out = res.stdout.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
        print(safe_out)
    if res.stderr:
        safe_err = res.stderr.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
        print(f"[STDERR]: {safe_err}")
    if check and res.returncode != 0:
        raise RuntimeError(f"Remote command failed with exit code {res.returncode}")
    return res


def run_scp(local_file: str, remote_dest: str):
    """Uploads file to remote host."""
    print(f"[*] Uploading {local_file} to {REMOTE_HOST}:{remote_dest}...")
    res = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", local_file, f"{REMOTE_HOST}:{remote_dest}"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if res.returncode != 0:
        raise RuntimeError(f"SCP failed: {res.stderr}")
    print("[+] Upload complete.")


def main():
    print("==================================================")
    print("FULCRUM CLUSTER A — DEPLOYMENT & VERIFICATION")
    print(f"Remote Host: {REMOTE_HOST}")
    print("==================================================")
    
    # 1. Prepare files
    create_env_file()
    create_deployment_archive()
    
    # 2. Upload archive to host
    run_scp(ARCHIVE_NAME, "/home/pravin/")
    
    # 3. Unpack archive on remote host
    unpack_cmd = f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR} && tar -xzf /home/pravin/{ARCHIVE_NAME} -C {REMOTE_DIR} && chmod +x {REMOTE_DIR}/scripts/*.sh"
    run_ssh_command(unpack_cmd)
    
    # 4. Execute the one-command production deploy script
    deploy_cmd = f"cd {REMOTE_DIR} && ./scripts/deploy.sh"
    run_ssh_command(deploy_cmd)
    
    # 5. Check status
    print("\n[*] Checking status via ./scripts/status.sh...")
    run_ssh_command(f"cd {REMOTE_DIR} && ./scripts/status.sh")
    
    # 6. Run failure isolation tests inside container
    print("\n[*] Running failure isolation test suite inside container...")
    run_ssh_command("docker exec fulcrum-app python -m pytest tests/test_failure_isolation.py -v")
    
    # 7. Run cross-session isolation tests inside container
    print("\n[*] Running cross-session isolation test suite inside container...")
    run_ssh_command("docker exec fulcrum-app python -m pytest tests/test_cross_session_isolation.py -v")
    
    # 8. Run concurrency load test (10, 25, 50 users) inside container
    print("\n[*] Running concurrency load test suite inside container...")
    run_ssh_command("docker exec fulcrum-app python tests/test_concurrency_load.py")
    
    print("\n==================================================")
    print("[SUCCESS] ALL DEPLOYMENT & VERIFICATION STEPS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    main()
