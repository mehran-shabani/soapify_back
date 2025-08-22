-- Optional MySQL initialization script
-- This file is automatically executed when the MySQL container is first created

-- Set character encoding
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Create database if not exists (backup)
CREATE DATABASE IF NOT EXISTS soapify CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant privileges (backup)
-- Note: User creation is handled by environment variables in docker-compose.yml

-- Optional: Create additional indexes or initial data
-- Example:
-- USE soapify;
-- CREATE INDEX idx_example ON table_name(column_name);