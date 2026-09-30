# NashForge for the Chipzen upload track. Built from container/upload/ (container/package.py writes it):
#   docker build -t nashforge:v5x container/upload
#   docker save nashforge:v5x | gzip > nashforge.tar.gz
# The base is the SDK starter's, pinned to the same digest. The starter's Cython stage is left out: it
# hides .py source, and this source is public; what the image carries that is not is the ladder.
# The built image is capped at 200 MB, so pip and setuptools go once the requirements are in, with
# numpy's tests and every __pycache__.
FROM python:3.12-slim@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /bot

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip uninstall -y pip setuptools wheel \
    && find /usr/local/lib/python3.12 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib/python3.12 -type d -name tests -exec rm -rf {} + 2>/dev/null; \
    true

# The user first and the files copied as theirs: a `chown -R` afterwards copied all 25 MB into a second layer.
RUN groupadd --system --gid 10001 bot && \
    useradd --system --uid 10001 --gid bot --home-dir /bot --shell /usr/sbin/nologin bot
COPY --chown=10001:10001 . /bot/
USER 10001

ENTRYPOINT ["python", "-u", "/bot/main.py"]
