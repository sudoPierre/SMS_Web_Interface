CREATE OR REPLACE FUNCTION create_user_if_not_exists()
RETURNS trigger AS $$
DECLARE
    exists_in_users BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM users
        WHERE phone_number = NEW.phone_number
    ) INTO exists_in_users;
    IF (NOT exists_in_users) THEN
        INSERT INTO users (phone_number) VALUES (NEW.phone_number);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_on_messages_insert ON messages;
CREATE TRIGGER trigger_on_messages_insert
AFTER INSERT ON messages
FOR EACH ROW EXECUTE FUNCTION create_user_if_not_exists();

CREATE OR REPLACE FUNCTION notify_worker()
RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'pending' AND NEW.direction = 'outbound' THEN
        PERFORM pg_notify('worker_channel', NEW.id::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_notify_worker_on_pending_message ON messages;
CREATE TRIGGER trigger_notify_worker_on_pending_message
AFTER INSERT ON messages
FOR EACH ROW EXECUTE FUNCTION notify_worker();
