#!/bin/bash
set -e

cd ~

echo "Setting up Frappe Bench for CI..."

# Install bench
pip install frappe-bench

# Initialize bench
bench init --skip-redis-config-generation --frappe-branch version-15 frappe-bench

cd frappe-bench

# Use containers for services
bench set-config -g db_host 127.0.0.1
bench set-config -g db_port 3306
bench set-config -g redis_cache "${REDIS_CACHE}"
bench set-config -g redis_queue "${REDIS_QUEUE}"

# Get the app
echo "Getting tweaks app from ${GITHUB_WORKSPACE}..."
bench get-app tweaks "${GITHUB_WORKSPACE}"

# Create test site
echo "Creating test site..."
bench new-site test_site --db-root-password "${DB_ROOT_PASSWORD}" --admin-password admin --no-mariadb-socket

# Install app on test site
echo "Installing tweaks app..."
bench --site test_site install-app tweaks

# Set developer mode
bench --site test_site set-config developer_mode 1

echo "Setup complete!"
