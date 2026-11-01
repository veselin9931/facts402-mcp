# Image for directories that build and inspect servers (Glama). Installs the published PyPI release.
FROM python:3.12-slim
LABEL io.modelcontextprotocol.server.name="com.facts402/facts402-mcp"
RUN pip install --no-cache-dir facts402-mcp==0.1.0
ENTRYPOINT ["facts402-mcp"]
