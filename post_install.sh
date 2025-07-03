#!/bin/bash
export LLAMA_CUBLAS=1
export CMAKE_ARGS="-DLLAMA_CUBLAS=on"
export FORCE_CMAKE=1

pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir