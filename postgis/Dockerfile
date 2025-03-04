FROM postgis/postgis:15-3.5-alpine

# Optional: Set up an entrypoint script to ensure PostGIS is always enabled
COPY init-postgis.sh /docker-entrypoint-initdb.d/init-postgis.sh
RUN chmod +x /docker-entrypoint-initdb.d/init-postgis.sh
