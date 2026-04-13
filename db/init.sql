DROP TABLE IF EXISTS messages;

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    body TEXT NOT NULL,
    direction VARCHAR(10) CHECK (direction IN ('inbound', 'outbound')),
    status VARCHAR(20) DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    activated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);