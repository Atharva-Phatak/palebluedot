#!/bin/sh

# Load environment variables from .env file
set -o allexport
. .env
set +o allexport

echo "Infisical secrets loaded into environment."
