-- Admins can manage the whitelist by SMS (/user). Only the web UI grants this flag.
ALTER TABLE authorized_numbers
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
