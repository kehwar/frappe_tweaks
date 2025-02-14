# Site: development.localhost

## Drop site

bench drop-site --no-backup --root-password 123 development.localhost

## Start new site

bench new-site development.localhost --admin-password admin --db-root-password 123

## Uninstall apps

bench --site development.localhost uninstall-app tweaks --yes --no-backup

## Install apps

bench --site development.localhost install-app erpnext
bench --site development.localhost install-app tweaks

## Backup

bench --site development.localhost backup --backup-path "backups"

## Restore

bench --site development.localhost restore --db-root-password 123 "backups/20250115_093910-development_localhost-database.sql.gz"

## Migrate

bench --site development.localhost migrate

## Run patch

bench --site development.localhost run-patch --force tweaks.custom.patches.2025.2025_01_17__add_workflow_field

# Bench

bench start

bench set-config -g server_script_enabled 1

bench update --reset --no-backup