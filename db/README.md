# Datebase structure

| Column        | Type         | Constraint        | Description                          |
|:--------------|:-------------|:------------------|:-------------------------------------|
| id            | SERIAL       | PRIMARY KEY       | Unique auto-incrementing ID          |
| phone_number  | VARCHAR(20)  | NOT NULL          | Phone number in international format |
| body          | TEXT         | NOT NULL          | The SMS message content              |
| direction     | VARCHAR(10)  | INBOUND/OUTBOUND  | Direction of the message             |
| status        | VARCHAR(20)  | DEFAULT 'pending' | Status (pending, sent, etc.)         |
| error_message | TEXT         | NULLABLE          | Error log if delivery fails          |
| created_at    | TIMESTAMPTZ  | DEFAULT NOW()     | Creation timestamp                   |
| updated_at    | TIMESTAMPTZ  | DEFAULT NOW()     | Last update timestamp                |