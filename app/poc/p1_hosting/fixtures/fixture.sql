-- Minimal synthetic fixture for the Windows CI smoke test (no corpus content; public Act titles only).
DROP TABLE IF EXISTS units; DROP TABLE IF EXISTS documents;
CREATE TABLE units(unit_id text PRIMARY KEY, doc_id text NOT NULL, doc_type text, title text, body text, tsv tsvector);
CREATE TABLE documents(doc_id text PRIMARY KEY, doc_type text, title text, meta jsonb, pdf_file text);
INSERT INTO units(unit_id, doc_id, doc_type, title, body) VALUES
 ('fx-1', 'fx-army-act', 'act', 'The Army Act, 1950', 'general court martial summary court martial commanding officer disability pension'),
 ('fx-2', 'fx-aft-act', 'act', 'The Armed Forces Tribunal Act, 2007', 'original application tribunal appeal against court martial'),
 ('fx-3', 'fx-judgment', 'judgment', 'Fixture v. Union of India', 'disability pension attributable to or aggravated by military service');
UPDATE units SET tsv = setweight(to_tsvector('english', title), 'A') || setweight(to_tsvector('english', body), 'B');
CREATE INDEX units_tsv ON units USING gin(tsv);
INSERT INTO documents VALUES
 ('fx-army-act', 'act', 'The Army Act, 1950', '{"doc_id": "fx-army-act", "title": "The Army Act, 1950"}', 'fixture.pdf'),
 ('fx-aft-act', 'act', 'The Armed Forces Tribunal Act, 2007', '{"doc_id": "fx-aft-act"}', NULL),
 ('fx-judgment', 'judgment', 'Fixture v. Union of India', '{"doc_id": "fx-judgment"}', NULL);
