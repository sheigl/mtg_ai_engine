FROM python:3.11-slim

# Create a non-root user
# Define arguments for username, UID, and GID
ARG USERNAME=sheigl
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user and group
RUN groupadd --gid 1000 sheigl && \
    useradd --uid 1000 --gid 1000 -m sheigl -s /bin/bash && \
    apt-get update && \
    apt-get install -y sudo && \
    echo "sheigl ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/sheigl && \
    chmod 0440 /etc/sudoers.d/sheigl

RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*

# Switch to the new user
USER sheigl



# Set working directory
WORKDIR /home/sheigl

# Install system dependencies

# Set environment variables
ENV HOME=/home/sheigl
ENV PYTHONPATH=/home/sheigl

# Install Python dependencies (if needed)
# COPY requirements.txt .
# RUN pip install -r requirements.txt
# Set default command (optional)
CMD ["/bin/bash"]