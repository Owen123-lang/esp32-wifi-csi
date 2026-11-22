FROM ubuntu:24.04 AS firmware
ENV IDF_PATH=/opt/esp/idf \
    IDF_TOOLS_PATH=/opt/esp/tools \
    IDF_PYTHON_ENV_PATH=/opt/esp/python
ENV PATH="${IDF_PATH}/tools:${IDF_PYTHON_ENV_PATH}/bin:/opt/esp/tools/tools/xtensa-esp-elf/esp-14.2.0_20250730/xtensa-esp-elf/bin:${PATH}"
RUN apt-get update \
    && apt-get install -y --no-install-recommends bison ca-certificates ccache cmake curl flex git gperf ninja-build python3 python3-venv xz-utils \
    && rm -rf /var/lib/apt/lists/*
RUN git -c advice.detachedHead=false clone --depth 1 --branch v5.4.3 \
        --recurse-submodules --shallow-submodules --jobs 8 https://github.com/espressif/esp-idf.git "$IDF_PATH" \
    && /usr/bin/python3 "$IDF_PATH/tools/idf_tools.py" install xtensa-esp-elf \
    && /usr/bin/python3 "$IDF_PATH/tools/idf_tools.py" install-python-env --features=core \
    && rm -rf "$IDF_TOOLS_PATH/dist" \
    && idf.py --version
WORKDIR /opt/espnow-firmware
COPY firmware/espnow-s3/ ./
COPY docker/build-firmware.sh /usr/local/bin/build-espnow-firmware
ENTRYPOINT ["bash", "/usr/local/bin/build-espnow-firmware"]

FROM firmware AS qemu
RUN apt-get update \
    && apt-get install -y --no-install-recommends libfdt1 libgcrypt20 libglib2.0-0t64 libpixman-1-0 libsdl2-2.0-0 libslirp0 \
    && rm -rf /var/lib/apt/lists/* \
    && /usr/bin/python3 "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa \
    && rm -rf "$IDF_TOOLS_PATH/dist"
ENV PATH="/opt/esp/tools/tools/qemu-xtensa/esp_develop_9.2.2_20250817/qemu/bin:${PATH}"
COPY docker/run-qemu.sh /usr/local/bin/run-espnow-qemu
ENTRYPOINT ["bash", "/usr/local/bin/run-espnow-qemu"]

FROM python:3.12-slim-bookworm AS simulator
WORKDIR /opt/espnow
COPY espnow/pyproject.toml ./
COPY espnow/src/ ./src/
RUN python -m pip install --no-cache-dir .
COPY espnow/configs/ ./configs/
COPY espnow/tests/ ./tests/
COPY docker/run-simulation.sh /usr/local/bin/run-espnow-simulation
CMD ["sh", "/usr/local/bin/run-espnow-simulation"]
