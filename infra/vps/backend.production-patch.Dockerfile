ARG BASE_IMAGE=cti-central-backend:current
FROM ${BASE_IMAGE}

USER root
COPY --chown=10001:10001 backend /app/backend
USER 10001
