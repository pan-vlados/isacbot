# syntax=docker/dockerfile:1
# `APP` ARG is only applicable for the src-layout.
ARG APP=src/isacbot \
    PYTHON_VERSION=3.12.8 \
    VIRTUAL_ENV=/opt/venv \
    INSTANCE_VOLUME=/usr/%{APP}/instance


FROM python:${PYTHON_VERSION}-slim AS builder


LABEL org.opencontainers.image.authors="pan.vlados.w@gmail.com"
ARG APP \
    VIRTUAL_ENV
# Add virtualenv into PATH.
ENV VIRTUAL_ENV=${VIRTUAL_ENV} \
    PATH="${VIRTUAL_ENV}/bin:$PATH" \
# Prevents Python from writing pyc files.
    PYTHONDONTWRITEBYTECODE=1 \
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
    PYTHONUNBUFFERED=1 \
# Ignore running pip as the 'root' user message.
    PIP_ROOT_USER_ACTION=ignore


WORKDIR /usr/${APP}


COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 && \
    python -m venv --copies $VIRTUAL_ENV && \
    pip install --upgrade pip && \
# Remove build dependencies and intermediate files after install.
    pip install --no-cache-dir --no-deps --require-hashes --only-binary :all: -r requirements.txt && \
    apt-get -y autoremove && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


FROM python:${PYTHON_VERSION}-slim AS runner


ARG APP \
    VIRTUAL_ENV \
    INSTANCE_VOLUME
ENV VIRTUAL_ENV=${VIRTUAL_ENV} \
    PATH="${VIRTUAL_ENV}/bin:$PATH" \
# Add PYTHONPATH for explicit python packages importing in project.
    PYTHONPATH=/usr/src \
# Set default timezone in container.
    TZ=Europe/Moscow


WORKDIR /usr/${APP}
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
    --system --group isacbot_user && \
# Add symlinks for /etc/localtime and /etc/timezone on TZ variable.
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy the virtual environment.
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
# Copy the source code into the container.
COPY ./${APP} LICENSE ./
# Give permissions for non-privileged user to db instance.
RUN chmod 700 ${INSTANCE_VOLUME} && chown -v isacbot_user:isacbot_user ${INSTANCE_VOLUME}
# Switch to the non-privileged user to run the application.
USER isacbot_user
# Run the application.
CMD ["python", "__main__.py"]