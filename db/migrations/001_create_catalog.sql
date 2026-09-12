CREATE TABLE IF NOT EXISTS catalog_parts (
    id SERIAL PRIMARY KEY,
    part VARCHAR(48) NOT NULL,
    vehicle_segment VARCHAR(32) NOT NULL,
    price NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    UNIQUE (part, vehicle_segment)
);

CREATE TABLE IF NOT EXISTS catalog_labor (
    id SERIAL PRIMARY KEY,
    operation VARCHAR(64) NOT NULL UNIQUE,
    labor_rate_per_hour NUMERIC(10,2) NOT NULL CHECK (labor_rate_per_hour >= 0)
);