#!/bin/bash
export CMAKE_ARGS="-DLLAMA_METAL=on"
export FORCE_CMAKE=1

pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir