# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12.8
FROM python:${PYTHON_VERSION}-slim AS base

LABEL org.opencontainers.image.authors="pan.vlados.w@gmail.com"

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1
# Ignore running pip as the 'root' user message.
ENV PIP_ROOT_USER_ACTION=ignore
# Add PYTHONPATH for explicit python packages importing in project.
ENV PYTHONPATH=/usr/src

ARG PROJECT_DIRPATH=src/isacbot


WORKDIR /usr/${PROJECT_DIRPATH}


# Create a non-fileprivileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    --system --group isacbot_user


RUN apt-get update && apt-get install -y --no-install-recommends && \
    apt-get install sqlite3 && \
    pip install --upgrade pip && \
    # chown -v isacbot_user:isacbot_user requirements.txt && \
# Remove build dependencies and intermediate files after install.
    apt-get clean && rm -rf /var/lib/apt/lists/*


COPY LICENSE requirements.txt ./
# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install --no-cache-dir --require-hashes --only-binary :all: -r requirements.txt
# Copy the source code into the container. Please note that
# the `PROJECT_DIRPATH` is only applicable for the src-layout.
COPY ./${PROJECT_DIRPATH} .

# Give permissions for non-privileged user to db instance.
RUN chmod 700 ./instance && chown -v isacbot_user:isacbot_user ./instance

# Switch to the non-privileged user to run the application.
USER isacbot_user

# Run the application.
CMD ["python", "__main__.py"]