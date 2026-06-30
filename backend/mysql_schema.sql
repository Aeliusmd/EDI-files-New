CREATE DATABASE IF NOT EXISTS edi_835_converter
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE edi_835_converter;

CREATE TABLE IF NOT EXISTS edi_835_imports (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  filename VARCHAR(255) NOT NULL,
  file_type VARCHAR(100) NOT NULL,
  transaction_count INT NOT NULL DEFAULT 0,
  claim_count INT NOT NULL DEFAULT 0,
  service_line_count INT NOT NULL DEFAULT 0,
  total_payment_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  raw_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS edi_835_claim_rows (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  import_id BIGINT UNSIGNED NOT NULL,
  claim_id VARCHAR(100) NULL,
  patient_name VARCHAR(255) NULL,
  payer_name VARCHAR(255) NULL,
  payee_name VARCHAR(255) NULL,
  payment_date VARCHAR(20) NULL,
  payment_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  claim_billed_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  claim_paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  procedure_code VARCHAR(80) NULL,
  service_date VARCHAR(20) NULL,
  service_paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  adjustment_details TEXT NULL,
  row_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_edi_835_claim_rows_import_id (import_id),
  KEY idx_edi_835_claim_rows_claim_id (claim_id),
  CONSTRAINT fk_edi_835_claim_rows_import
    FOREIGN KEY (import_id) REFERENCES edi_835_imports (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
