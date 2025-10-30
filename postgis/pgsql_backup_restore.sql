
-- psql -U younes -d SDMB -f 'C:\Users\youmt\Documents\ArcGIS\QGIS\backup-dbgeste.sql'

-- docker cp backup-dbgeste.bak.sql majal_postgres:/backup.sql
-- docker exec -it majal_postgres bash -c "psql -U StreetAdmin2025 -d EcoGeste -f /backup.sql"
-- "C:\Program Files\PostgreSQL\16\pgAdmin 4\runtime\pg_dump.exe" --file "C:\\Users\\youmt\\PROGRA~1\\DBACKUP\\pgsql\\ecogis3.sql" --host "192.168.1.77" --port "5438" --username "StreetAdmin2025" --password="ViewPasswo2025" --format="plain" --section=data --inserts --on-conflict-do-nothing --create --clean --if-exists --quote-all-identifiers "ecogis"


"C:\Program Files\PostgreSQL\16\pgAdmin 4\runtime\pg_dump.exe" --file "C:\\Users\\youmt\\PROGRA~1\\DBACKUP\\pgsql\\ECOGES~2.SQL" --host "192.168.1.77" --port "5438" --username "StreetAdmin2025" --password="ViewPasswo2025" --no-password --format=p --schema-only --verbose "EcoGeste"