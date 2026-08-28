FROM python:3.12-slim

WORKDIR /app

# Copy and install A2A SDK
COPY setup.py README.md /app/
COPY src/ /app/src/
COPY tools/ /app/tools/
COPY manifest.json /app/
RUN pip install --no-cache-dir -e . && pip install --no-cache-dir requests tonsdk pynacl httpx

ENV PYTHONUNBUFFERED=1
ENV GSTD_WALLET_PATH=/data/.gstd/wallet.json
ENV GSTD_API_URL=https://platform.gstdtoken.com
ENV GSTD_DEFAULT_MODEL=llama3.2:3b
ENV OPENCLAW_ENABLED=true
ENV OPENCLAW_API_BASE=https://platform.gstdtoken.com/api/v1/openclaw

# Expose port for local API (optional)
EXPOSE 8400

CMD ["python3", "-m", "gstd_a2a.main"]
