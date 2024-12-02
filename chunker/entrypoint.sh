#!/bin/sh

# Ensure shared_data directory exists
mkdir -p /shared_data

# Copy data files to shared volume
cp -r /app/data/* /shared_data/

# Make sure files are readable
chmod -R 755 /shared_data

# Execute the main command
exec "$@"
