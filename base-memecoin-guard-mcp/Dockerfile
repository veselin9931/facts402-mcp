# Image for directories that build and inspect servers (Glama). Installs the published PyPI release.
FROM python:3.12-slim
LABEL io.modelcontextprotocol.server.name="com.facts402/base-memecoin-guard"
RUN pip install --no-cache-dir base-memecoin-guard-mcp==0.1.0
ENTRYPOINT ["base-memecoin-guard-mcp"]
