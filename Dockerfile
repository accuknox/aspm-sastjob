FROM python:3.13-alpine3.21 AS base
ENV BUILDWORKDIR=/app
WORKDIR $BUILDWORKDIR
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

FROM base AS build
WORKDIR $BUILDWORKDIR
COPY ./requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir $BUILDWORKDIR/wheels -r requirements.txt

FROM base AS final
WORKDIR $BUILDWORKDIR
COPY --from=build $BUILDWORKDIR/wheels ./wheels
RUN pip install --upgrade pip && \
    pip install  --no-cache-dir --no-cache ./wheels/* && rm -rf ./wheels

COPY . . 
RUN pip install -e .

ENTRYPOINT [ "accuknox-sq-sast" ]