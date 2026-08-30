CREATE TABLE transfers (
  id INTEGER PRIMARY KEY
);
CREATE INDEX idx_transfers_id ON transfers(id);
CREATE VIEW active_transfers AS SELECT * FROM transfers;
CREATE FUNCTION compute_hash(x TEXT) RETURNS TEXT AS $$ $$ LANGUAGE sql;
