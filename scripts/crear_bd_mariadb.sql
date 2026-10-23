-- Creación de la base y el usuario de MariaDB para Cinema.
-- Ejecutar como administrador de MariaDB:
--   sudo mariadb < scripts/crear_bd_mariadb.sql
--
-- Las credenciales por defecto coinciden con las variables CINEMA_DB_* que
-- documenta el README. Cámbialas en producción.

CREATE DATABASE IF NOT EXISTS cinema
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'cinema'@'localhost' IDENTIFIED BY 'cinema123';
CREATE USER IF NOT EXISTS 'cinema'@'127.0.0.1' IDENTIFIED BY 'cinema123';

GRANT ALL PRIVILEGES ON cinema.* TO 'cinema'@'localhost';
GRANT ALL PRIVILEGES ON cinema.* TO 'cinema'@'127.0.0.1';

FLUSH PRIVILEGES;
