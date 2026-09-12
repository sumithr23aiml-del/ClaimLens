CREATE TABLE IF NOT EXISTS policies (
    id VARCHAR(64) PRIMARY KEY,
    holder_name_enc TEXT NOT NULL,
    vehicle JSONB NOT NULL,
    coverage JSONB NOT NULL,
    deductible NUMERIC(10,2) NOT NULL DEFAULT 0,
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    id SERIAL PRIMARY KEY,
    policy_id VARCHAR(64) NOT NULL REFERENCES policies(id),
    incident JSONB NOT NULL,
    policy_snapshot JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'received',
    band VARCHAR(32),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claim_images (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    uri TEXT NOT NULL,
    checklist_slot VARCHAR(64) NOT NULL,
    exif JSONB,
    quality REAL,
    phash VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);