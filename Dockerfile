FROM python:3.12-slim

WORKDIR /app

# Copy and install A2A SDK
COPY python-sdk/ /app/python-sdk/
COPY setup.py /app/
COPY src/ /app/src/
COPY tools/ /app/tools/
COPY manifest.json /app/
RUN pip install --no-cache-dir -e . && pip install --no-cache-dir requests tonsdk pynacl httpx

ENV PYTHONUNBUFFERED=1
ENV GSTD_WALLET_PATH=/data/.gstd/wallet.json
ENV GSTD_API_URL=https://app.gstdtoken.com
ENV GSTD_DEFAULT_MODEL=groq/compound
ENV OPENCLAW_ENABLED=true
ENV OPENCLAW_API_BASE=https://api.gstdtoken.com/api/v1/openclaw

# Expose port for local API (optional)
EXPOSE 8400

CMD ["python3", "-m", "gstd_a2a.main"]
