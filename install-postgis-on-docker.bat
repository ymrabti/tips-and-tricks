docker exec -it <your_postgres_container_id> bash

apt update && apt install -y postgis postgresql-15-postgis-3

psql -U postgres -d postgres

CREATE EXTENSION postgis;
SELECT PostGIS_Version();

-- line-per line
-- Create the template database
    CREATE DATABASE postgis_temp_db;
-- Connect to the template database
    \c postgis_temp_db;
-- Enable PostGIS extensions
    CREATE EXTENSION postgis;
    CREATE EXTENSION postgis_topology;
-- Make the database a template (prevents accidental modifications)
    UPDATE pg_database SET datistemplate = TRUE WHERE datname = 'postgis_temp_db';


CREATE DATABASE my_spatial_db TEMPLATE postgis_temp_db;

SELECT PostGIS_Version();

