-- ============================================================
-- ClaimLens — M1 schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- POLICY MASTER
-- ============================================================

CREATE TABLE IF NOT EXISTS policy_products (
    product_id VARCHAR(30) PRIMARY KEY,
    product_name VARCHAR(160) NOT NULL,
    line_of_business VARCHAR(20) NOT NULL
        CHECK (line_of_business IN ('motor', 'health', 'property', 'travel', 'liability')),
    base_deductible NUMERIC(12,2) NOT NULL DEFAULT 0,
    waiting_period_days INT NOT NULL DEFAULT 0,
    depreciation_schedule JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_ref VARCHAR(64) UNIQUE NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    date_of_birth DATE,
    email VARCHAR(200),
    phone VARCHAR(30),
    city VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_number VARCHAR(40) UNIQUE NOT NULL,
    product_id VARCHAR(30) NOT NULL
        REFERENCES policy_products(product_id),
    customer_id UUID NOT NULL
        REFERENCES customers(customer_id) ON DELETE CASCADE,
    inception_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'lapsed', 'cancelled', 'expired')),
    CHECK (expiry_date > inception_date)
);

CREATE INDEX IF NOT EXISTS idx_policies_customer
    ON policies(customer_id);

CREATE TABLE IF NOT EXISTS policy_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL
        REFERENCES policies(policy_id) ON DELETE CASCADE,
    version_no INT NOT NULL CHECK (version_no >= 1),
    effective_from DATE NOT NULL,
    effective_to DATE,
    endorsement_reason VARCHAR(200),
    UNIQUE (policy_id, version_no)
);

CREATE TABLE IF NOT EXISTS coverages (
    coverage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL
        REFERENCES policy_versions(version_id) ON DELETE CASCADE,
    peril VARCHAR(60) NOT NULL,
    sum_insured NUMERIC(14,2) NOT NULL CHECK (sum_insured > 0),
    sub_limit NUMERIC(14,2),
    deductible NUMERIC(12,2) NOT NULL DEFAULT 0,
    coinsurance_pct NUMERIC(5,2) NOT NULL DEFAULT 0
        CHECK (coinsurance_pct BETWEEN 0 AND 100),
    UNIQUE (version_id, peril)
);

-- ============================================================
-- CLAIM
-- ============================================================

CREATE TABLE IF NOT EXISTS claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_number VARCHAR(30) UNIQUE NOT NULL,
    policy_id UUID NOT NULL
        REFERENCES policies(policy_id),
    peril VARCHAR(60) NOT NULL,
    loss_date DATE NOT NULL,
    loss_location VARCHAR(200),
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_amount NUMERIC(14,2)
        CHECK (claimed_amount >= 0),
    description TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'registered'
        CHECK (status IN (
            'registered',
            'documents_pending',
            'extracted',
            'assessed',
            'decided',
            'settled',
            'rejected',
            'withdrawn'
        )),
    assigned_to VARCHAR(80)
);

CREATE INDEX IF NOT EXISTS idx_claims_status
    ON claims(status, reported_at DESC);

CREATE INDEX IF NOT EXISTS idx_claims_policy
    ON claims(policy_id, loss_date DESC);

CREATE TABLE IF NOT EXISTS policy_snapshots (
    claim_id UUID PRIMARY KEY
        REFERENCES claims(claim_id) ON DELETE CASCADE,
    policy_number VARCHAR(40) NOT NULL,
    product_id VARCHAR(30) NOT NULL,
    version_no INT NOT NULL,
    inception_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    terms JSONB NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- DOCUMENTS & EXTRACTION
-- ============================================================

CREATE TABLE IF NOT EXISTS claim_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL
        REFERENCES claims(claim_id) ON DELETE CASCADE,
    document_type VARCHAR(40) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    storage_uri TEXT NOT NULL,
    mime_type VARCHAR(100),
    page_count INT,
    checksum_sha256 CHAR(64) NOT NULL,
    ocr_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (ocr_status IN (
            'pending',
            'done',
            'failed',
            'not_required'
        )),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (claim_id, checksum_sha256)
);

CREATE INDEX IF NOT EXISTS idx_docs_claim
    ON claim_documents(claim_id, document_type);

CREATE TABLE IF NOT EXISTS extracted_fields (
    field_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL
        REFERENCES claims(claim_id) ON DELETE CASCADE,
    document_id UUID NOT NULL
        REFERENCES claim_documents(document_id) ON DELETE CASCADE,
    field_name VARCHAR(60) NOT NULL,
    field_value TEXT,
    normalised_value TEXT,
    page_number INT,
    bbox JSONB,
    confidence REAL NOT NULL
        CHECK (confidence BETWEEN 0 AND 1),
    extractor_version VARCHAR(40) NOT NULL DEFAULT 'm1-placeholder',
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fields_claim
    ON extracted_fields(claim_id, field_name);

CREATE TABLE IF NOT EXISTS claim_line_items (
    line_id BIGSERIAL PRIMARY KEY,
    claim_id UUID NOT NULL
        REFERENCES claims(claim_id) ON DELETE CASCADE,
    document_id UUID
        REFERENCES claim_documents(document_id) ON DELETE SET NULL,
    line_no INT NOT NULL,
    description VARCHAR(300) NOT NULL,
    part_category VARCHAR(40),
    claimed_amount NUMERIC(14,2) NOT NULL
        CHECK (claimed_amount >= 0),
    quantity NUMERIC(10,2) NOT NULL DEFAULT 1,
    is_admissible BOOLEAN,
    UNIQUE (claim_id, line_no)
);

-- ============================================================
-- DECISION
-- ============================================================

CREATE TABLE IF NOT EXISTS fraud_indicators (
    indicator_code VARCHAR(30) NOT NULL,
    version INT NOT NULL,
    description TEXT NOT NULL,
    weight INT NOT NULL
        CHECK (weight BETWEEN 0 AND 100),
    params JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (indicator_code, version)
);

CREATE TABLE IF NOT EXISTS fraud_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL
        REFERENCES claims(claim_id) ON DELETE CASCADE,
    score INT NOT NULL
        CHECK (score BETWEEN 0 AND 100),
    band VARCHAR(20) NOT NULL
        CHECK (band IN (
            'clear',
            'monitor',
            'manual_review',
            'siu_referral'
        )),
    indicator_hits JSONB NOT NULL DEFAULT '[]',
    model_score DOUBLE PRECISION,
    scorer_version VARCHAR(40) NOT NULL DEFAULT 'm1-rules-only',
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fraud_claim
    ON fraud_assessments(claim_id, assessed_at DESC);

CREATE TABLE IF NOT EXISTS claim_decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL
        REFERENCES claims(claim_id) ON DELETE CASCADE,
    outcome VARCHAR(20) NOT NULL
        CHECK (outcome IN (
            'approved',
            'partially_approved',
            'rejected',
            'referred'
        )),
    payable_amount NUMERIC(14,2) NOT NULL
        CHECK (payable_amount >= 0),
    rejection_reason VARCHAR(300),
    decided_by VARCHAR(80) NOT NULL,
    is_automated BOOLEAN NOT NULL DEFAULT FALSE,
    override_of UUID
        REFERENCES claim_decisions(decision_id),
    override_reason TEXT,
    rationale TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_claim
    ON claim_decisions(claim_id, decided_at DESC);

CREATE TABLE IF NOT EXISTS settlement_lines (
    id BIGSERIAL PRIMARY KEY,
    decision_id UUID NOT NULL
        REFERENCES claim_decisions(decision_id) ON DELETE CASCADE,
    line_id BIGINT
        REFERENCES claim_line_items(line_id) ON DELETE SET NULL,
    component VARCHAR(30) NOT NULL
        CHECK (component IN (
            'claimed',
            'inadmissible',
            'depreciation',
            'deductible',
            'coinsurance',
            'sub_limit_cap',
            'sum_insured_cap',
            'payable'
        )),
    amount NUMERIC(14,2) NOT NULL,
    note VARCHAR(200)
);

CREATE INDEX IF NOT EXISTS idx_settlement_decision
    ON settlement_lines(decision_id);