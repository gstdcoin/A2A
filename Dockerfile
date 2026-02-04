# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsodium-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies clearly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . /app

# Install the package itself (for setup.py entrypoints)
RUN pip install .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Set MCP transport to SSE for web-hosted agents
ENV MCP_TRANSPORT=sse
ENV PORT=8000

# Run the MCP server
CMD ["python", "main.py"]
