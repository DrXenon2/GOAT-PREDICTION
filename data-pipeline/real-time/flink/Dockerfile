# Apache Flink Dockerfile for Goat Prediction Real-time Processing
# Multi-stage build for optimized image size and security

# ==============================================================================
# STAGE 1: BASE BUILDER
# ==============================================================================
FROM eclipse-temurin:21-jdk-jammy AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-venv \
    libatlas-base-dev \
    libgfortran5 \
    libopenblas-dev \
    liblapack-dev \
    git \
    maven \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install Python dependencies
COPY requirements-flink.txt /tmp/requirements-flink.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements-flink.txt

# ==============================================================================
# STAGE 2: FLINK BASE
# ==============================================================================
FROM eclipse-temurin:21-jre-jammy AS flink-base

# Flink version
ENV FLINK_VERSION=1.18.1 \
    SCALA_VERSION=2.12 \
    FLINK_HOME=/opt/flink \
    JAVA_HOME=/opt/java/openjdk \
    PATH=$PATH:/opt/flink/bin

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    python3-venv \
    libgfortran5 \
    libopenblas-dev \
    liblapack-dev \
    curl \
    netcat \
    net-tools \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system --gid 9999 flink && \
    useradd --system --no-create-home --uid 9999 --gid flink flink

# Create directories
RUN mkdir -p ${FLINK_HOME} \
    && mkdir -p /opt/flink/logs \
    && mkdir -p /opt/flink/plugins \
    && mkdir -p /opt/flink/lib \
    && mkdir -p /opt/flink/checkpoints \
    && mkdir -p /opt/flink/savepoints \
    && mkdir -p /opt/flink/ha \
    && mkdir -p /opt/flink/userlib \
    && chown -R flink:flink ${FLINK_HOME} \
    && chown -R flink:flink /opt/flink

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ==============================================================================
# STAGE 3: FLINK DOWNLOAD AND SETUP
# ==============================================================================
FROM flink-base AS flink-download

# Download and extract Flink
RUN wget -q https://archive.apache.org/dist/flink/flink-${FLINK_VERSION}/flink-${FLINK_VERSION}-bin-scala_${SCALA_VERSION}.tgz -O /tmp/flink.tgz \
    && tar xzf /tmp/flink.tgz -C /opt \
    && mv /opt/flink-${FLINK_VERSION}/* ${FLINK_HOME} \
    && rm /tmp/flink.tgz \
    && rm -rf /opt/flink-${FLINK_VERSION}

# ==============================================================================
# STAGE 4: FLINK WITH CONNECTORS
# ==============================================================================
FROM flink-download AS flink-connectors

WORKDIR ${FLINK_HOME}

# Download required connectors and libraries
RUN wget -q -P ${FLINK_HOME}/lib \
    https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.2-1.18/flink-sql-connector-kafka-3.0.2-1.18.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-connector-files/3.0.2-1.18/flink-connector-files-3.0.2-1.18.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-connector-base/3.0.2-1.18/flink-connector-base-3.0.2-1.18.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-connector-prometheus_${SCALA_VERSION}/1.18.1/flink-connector-prometheus_${SCALA_VERSION}-1.18.1.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-json/${FLINK_VERSION}/flink-json-${FLINK_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-csv/${FLINK_VERSION}/flink-csv-${FLINK_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/flink/flink-parquet/${FLINK_VERSION}/flink-parquet-${FLINK_VERSION}.jar

# Download database drivers
RUN wget -q -P ${FLINK_HOME}/lib \
    https://jdbc.postgresql.org/download/postgresql-42.6.0.jar \
    https://repo1.maven.org/maven2/redis/clients/jedis/5.0.2/jedis-5.0.2.jar

# Download Python dependencies for PyFlink
RUN wget -q -P ${FLINK_HOME}/opt \
    https://repo1.maven.org/maven2/org/apache/flink/flink-python_${SCALA_VERSION}/${FLINK_VERSION}/flink-python_${SCALA_VERSION}-${FLINK_VERSION}.jar

# Download Apache Beam for Python runner
RUN wget -q -P ${FLINK_HOME}/lib \
    https://repo1.maven.org/maven2/org/apache/beam/beam-runners-flink-1.18/2.50.0/beam-runners-flink-1.18-2.50.0.jar \
    https://repo1.maven.org/maven2/org/apache/beam/beam-sdks-java-core/2.50.0/beam-sdks-java-core-2.50.0.jar \
    https://repo1.maven.org/maven2/org/apache/beam/beam-sdks-java-io-kafka/2.50.0/beam-sdks-java-io-kafka-2.50.0.jar \
    https://repo1.maven.org/maven2/org/apache/beam/beam-sdks-java-extensions-sql/2.50.0/beam-sdks-java-extensions-sql-2.50.0.jar

# Download additional ML libraries
RUN wget -q -P ${FLINK_HOME}/userlib \
    https://repo1.maven.org/maven2/numpy/numpy/1.24.3/numpy-1.24.3.jar \
    https://repo1.maven.org/maven2/org/scipy/scipy/1.10.1/scipy-1.10.1.jar \
    https://repo1.maven.org/maven2/org/scikit-learn/scikit-learn/1.3.0/scikit-learn-1.3.0.jar \
    https://repo1.maven.org/maven2/pandas/pandas/2.0.3/pandas-2.0.3.jar

# ==============================================================================
# STAGE 5: FINAL FLINK IMAGE
# ==============================================================================
FROM flink-connectors AS flink-final

# Set working directory
WORKDIR ${FLINK_HOME}

# Environment variables
ENV FLINK_HOME=/opt/flink \
    FLINK_PROPERTIES="jobmanager.rpc.address: jobmanager" \
    PYFLINK_CLIENT_EXECUTABLE=python3 \
    PYTHONPATH="${FLINK_HOME}/opt/python:/opt/venv/lib/python3.10/site-packages:${PYTHONPATH}" \
    JAVA_OPTS="-Dorg.apache.flink.shaded.netty4.io.netty.tryReflectionSetAccessible=true \
               -Dorg.apache.flink.shaded.netty4.io.netty.eventLoopThreads=16 \
               -XX:+UseG1GC \
               -XX:MaxGCPauseMillis=200 \
               -XX:ParallelGCThreads=4 \
               -XX:ConcGCThreads=2 \
               -XX:+HeapDumpOnOutOfMemoryError \
               -XX:HeapDumpPath=/opt/flink/logs \
               -XX:OnOutOfMemoryError='kill -9 %p' \
               -Dlog4j.configurationFile=file:/opt/flink/conf/log4j-console.properties \
               -Dlogback.configurationFile=file:/opt/flink/conf/logback.xml"

# Copy configuration files
COPY conf/ ${FLINK_HOME}/conf/

# Copy Python jobs and utilities
COPY --chown=flink:flink jobs/ /opt/flink/jobs/
COPY --chown=flink:flink scripts/ /opt/flink/scripts/
COPY --chown=flink:flink utils/ /opt/flink/utils/

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy health check script
COPY healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Copy Python dependencies
COPY --from=builder /opt/venv /opt/venv

# Create Python job directories
RUN mkdir -p /opt/flink/python_jobs && \
    chown -R flink:flink /opt/flink/python_jobs

# Create data directories
RUN mkdir -p /opt/flink/data && \
    mkdir -p /opt/flink/checkpoints && \
    mkdir -p /opt/flink/savepoints && \
    chown -R flink:flink /opt/flink/data /opt/flink/checkpoints /opt/flink/savepoints

# Expose ports
EXPOSE 6123 8081 8082 9000 9001 9091 9092

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /healthcheck.sh

# Switch to non-root user
USER flink

# Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["standalone-job"]

# ==============================================================================
# STAGE 6: JOBMANAGER SPECIFIC
# ==============================================================================
FROM flink-final AS jobmanager

ENV FLINK_PROPERTIES="jobmanager.rpc.address: jobmanager \
                      jobmanager.memory.process.size: 4096m \
                      taskmanager.memory.process.size: 8192m \
                      taskmanager.numberOfTaskSlots: 8 \
                      parallelism.default: 4 \
                      high-availability: zookeeper \
                      high-availability.storageDir: file:///opt/flink/ha/ \
                      high-availability.zookeeper.quorum: zookeeper:2181 \
                      high-availability.zookeeper.path.root: /flink \
                      high-availability.cluster-id: /goat-prediction-flink \
                      state.backend: filesystem \
                      state.checkpoints.dir: file:///opt/flink/checkpoints \
                      state.savepoints.dir: file:///opt/flink/savepoints \
                      state.backend.fs.checkpointdir: file:///opt/flink/checkpoints \
                      execution.checkpointing.interval: 30000 \
                      execution.checkpointing.timeout: 600000 \
                      execution.checkpointing.min-pause: 5000 \
                      execution.checkpointing.max-concurrent-checkpoints: 1 \
                      execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION \
                      restart-strategy: fixed-delay \
                      restart-strategy.fixed-delay.attempts: 3 \
                      restart-strategy.fixed-delay.delay: 10s \
                      metrics.reporter.prom.class: org.apache.flink.metrics.prometheus.PrometheusReporter \
                      metrics.reporter.prom.port: 9250-9260 \
                      metrics.reporter.jmx.class: org.apache.flink.metrics.jmx.JMXReporter \
                      metrics.reporter.slf4j.class: org.apache.flink.metrics.slf4j.Slf4jReporter \
                      metrics.reporter.slf4j.interval: 60 SECONDS \
                      python.client.executable: python3 \
                      python.files: /opt/flink/jobs/ \
                      python.archives: /opt/venv \
                      python.executable: /opt/venv/bin/python3"

# Copy jobmanager specific configuration
COPY conf/jobmanager/ ${FLINK_HOME}/conf/

# Expose additional ports for jobmanager
EXPOSE 6123 8081

# Command for jobmanager
CMD ["jobmanager"]

# ==============================================================================
# STAGE 7: TASKMANAGER SPECIFIC
# ==============================================================================
FROM flink-final AS taskmanager

ENV FLINK_PROPERTIES="jobmanager.rpc.address: jobmanager \
                      taskmanager.memory.process.size: 8192m \
                      taskmanager.memory.managed.size: 4096m \
                      taskmanager.memory.network.min: 512m \
                      taskmanager.memory.network.max: 1024m \
                      taskmanager.memory.framework.off-heap.size: 256m \
                      taskmanager.memory.task.off-heap.size: 256m \
                      taskmanager.memory.jvm-metaspace.size: 512m \
                      taskmanager.memory.jvm-overhead.min: 256m \
                      taskmanager.memory.jvm-overhead.max: 512m \
                      taskmanager.numberOfTaskSlots: 8 \
                      taskmanager.memory.segment-size: 32kb \
                      taskmanager.network.memory.buffers-per-channel: 2 \
                      taskmanager.network.memory.floating-buffers-per-gate: 8 \
                      python.client.executable: python3 \
                      python.files: /opt/flink/jobs/ \
                      python.archives: /opt/venv \
                      python.executable: /opt/venv/bin/python3"

# Copy taskmanager specific configuration
COPY conf/taskmanager/ ${FLINK_HOME}/conf/

# Command for taskmanager
CMD ["taskmanager"]

# ==============================================================================
# STAGE 8: PYTHON JOB SPECIFIC
# ==============================================================================
FROM flink-final AS python-job-runner

# Additional Python dependencies for ML jobs
COPY requirements-ml.txt /tmp/requirements-ml.txt
RUN pip install -r /tmp/requirements-ml.txt

# Copy Python jobs with proper permissions
COPY --chown=flink:flink jobs/ /opt/flink/jobs/

# Set Python-specific environment variables
ENV PYTHONPATH="/opt/flink/jobs:/opt/venv/lib/python3.10/site-packages:${PYTHONPATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8

# Create Python virtual environment wrapper
COPY run-python-job.sh /run-python-job.sh
RUN chmod +x /run-python-job.sh

# Command for running Python jobs
CMD ["/run-python-job.sh"]

# ==============================================================================
# STAGE 9: DEVELOPMENT IMAGE
# ==============================================================================
FROM flink-final AS development

# Install development tools
USER root
RUN apt-get update && apt-get install -y \
    vim \
    nano \
    git \
    procps \
    lsof \
    netcat \
    telnet \
    iputils-ping \
    dnsutils \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Python development tools
RUN pip install \
    black \
    flake8 \
    mypy \
    pytest \
    pytest-cov \
    ipython \
    jupyter \
    notebook

# Copy development scripts
COPY --chown=flink:flink dev-scripts/ /opt/flink/dev-scripts/

# Switch back to flink user
USER flink

# Development entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["development"]
