ARG BASE_IMAGE=cti-external-sources:1.0.0
FROM ${BASE_IMAGE}

USER root
COPY backend /app/backend
COPY contracts /app/contracts
COPY config/sources.json \
     config/collection_settings.json \
     config/preprocessing_rules.json \
     config/privacy_rules.json \
     config/dark_web_sources.example.json \
     /app/config/
RUN chown -R --no-dereference 0:0 /app/backend /app/contracts /app/config \
    && find /app/backend /app/contracts /app/config -xdev -type d -exec chmod 0755 {} + \
    && find /app/backend /app/contracts /app/config -xdev -type f -exec chmod 0644 {} +
USER 10001:10001
