FROM python:3.12-slim

WORKDIR /app

# Copy and install A2A SDK
COPY python-sdk/ /app/python-sdk/
COPY setup.py /app/
RUN pip install --no-cache-dir -e . && pip install --no-cache-dir requests tonsdk pynacl

ENV PYTHONUNBUFFERED=1
ENV GSTD_WALLET_PATH=/data/.gstd/wallet.json

CMD ["python3", "-m", "gstd_a2a.main"]
