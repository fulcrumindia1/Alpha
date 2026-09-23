# ==============================================================================
# FULCRUM-INDIA (Cluster A) — Production Dockerfile for Hostinger KVM 2 & Dokploy
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install minimal OS dependencies for network healthcheck, fonts, and Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gcc \
    python3-dev \
    fonts-liberation \
    fonts-dejavu-core \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    && (apt-get install -y --no-install-recommends libasound2t64 || apt-get install -y --no-install-recommends libasound2 || true) \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create a dedicated non-root application user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /ms-playwright && \
    chown -R appuser:appuser /app /ms-playwright

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Playwright Chromium browser binary and system dependencies
RUN playwright install --with-deps chromium && \
    chown -R appuser:appuser /ms-playwright

# Copy application source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose internal Streamlit port
EXPOSE 8501

# Production health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Production startup command
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true", \
     "--theme.base=light", \
     "--theme.primaryColor=#2563EB", \
     "--theme.backgroundColor=#F8FAFC", \
     "--theme.secondaryBackgroundColor=#FFFFFF", \
     "--theme.textColor=#0F172A"]
