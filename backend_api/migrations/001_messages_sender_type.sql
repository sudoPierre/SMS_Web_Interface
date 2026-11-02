-- Who authored a message: a person (inbound SMS or the web UI), a /command reply, or the AI agent.
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS sender_type VARCHAR(10) NOT NULL DEFAULT 'human';

ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_sender_type_check;
ALTER TABLE messages
    ADD CONSTRAINT messages_sender_type_check
    CHECK (sender_type IN ('human', 'command', 'ai_agent'));
