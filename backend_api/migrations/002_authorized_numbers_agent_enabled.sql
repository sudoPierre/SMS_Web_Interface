-- Per-number switch for the AI agent, independent of the number's access to /commands.
ALTER TABLE authorized_numbers
    ADD COLUMN IF NOT EXISTS agent_enabled BOOLEAN NOT NULL DEFAULT TRUE;
