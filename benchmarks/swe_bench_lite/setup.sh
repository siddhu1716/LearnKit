#!/bin/bash
set -e

# setup_swebench.sh
# Installs swebench and datasets packages in the virtual environment.

echo "Installing swebench and datasets in the local virtual environment..."
.venv/bin/pip install swebench datasets

echo "Setup completed successfully!"
