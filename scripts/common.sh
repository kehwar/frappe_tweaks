# Site: development.localhost

## Drop site

bench drop-site --no-backup --root-password 123 development.localhost

## Start new site

bench new-site development.localhost --admin-password admin --db-root-password 123

## Install apps

bench --site development.localhost install-app erpnext
bench --site development.localhost install-app tweaks

## Backup

bench --site development.localhost backup --backup-path "backups"

## Restore

bench --site development.localhost restore --db-root-password 123 "backups/20250115_093910-development_localhost-database.sql.gz"

## Migrate

bench --site development.localhost migrate

# Bench

bench start
