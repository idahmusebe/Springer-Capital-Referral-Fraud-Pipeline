FROM python:3.11-slim

# Install Java 21 because PySpark requires Java
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Set Java environment for PySpark
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Set the working directory inside the container
WORKDIR /app

# Copy project dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code and input data
COPY src/ ./src/
COPY data/ ./data/

# Create output and profiling directories
RUN mkdir -p output profiling

# Run the referral pipeline when the container starts
CMD ["python", "src/referral_pipeline.py"]