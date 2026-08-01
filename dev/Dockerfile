# Home Assistant with this integration's manifest requirements baked in.
#
# Home Assistant normally installs a custom integration's requirements itself,
# lazily, the first time the integration is loaded. When that install does not
# happen the only symptom is "Invalid handler specified" in the UI and a bare
# ModuleNotFoundError in the log, which is a poor way to spend an afternoon.
#
# Installing them at build time makes startup deterministic, removes the
# network round-trip from the first config-flow attempt, and means the
# container works offline once built.

ARG HA_VERSION=stable
FROM ghcr.io/home-assistant/home-assistant:${HA_VERSION}

# Only manifest.json is copied, so the layer cache is reused until the
# requirements actually change. The integration source is bind-mounted at run
# time and is deliberately not part of the image.
COPY custom_components/catlink/manifest.json /tmp/manifest.json

# Same flags Home Assistant itself uses (see homeassistant.requirements.pip_kwargs
# and homeassistant.util.package.install_package), including core's constraint
# file so we cannot pull a version that breaks Home Assistant.
RUN python -m uv pip install --system \
      --index-strategy unsafe-first-match \
      --constraint /usr/src/homeassistant/homeassistant/package_constraints.txt \
      $(python -c "import json; print(' '.join(json.load(open('/tmp/manifest.json'))['requirements']))") \
    && rm /tmp/manifest.json
