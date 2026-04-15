# SMS Web Interface

`Development in progress ⚠️`

Web interface for Android SMS Gateway.

This project receives incoming SMS events from an Android gateway app and stores them in MySQL. It also exposes an API endpoint to queue outbound SMS messages from a ReactJS Web interface.

## Features

- Receive inbound SMS via webhook (`/webhook`)
- Accept outbound SMS requests from a web UI (`/api/messages/send`)
- Persist messages in PostgreSQL with direction and status
- Run everything with Docker Compose

## Stack

- ReactJS
- FastAPI (Python)
- PostgreSQL
- Docker + Docker Compose

## Project Structure

```text
.
├── docker-compose.yml
├── README.md
├── backend_api/
│   ├── Dockerfile
│   ├── main.py
│   ├── README.md
│   └── requirements.txt
├── db/
│   ├── init.sql
│   └── README.md
└── worker/
│   ├── Dockerfile
│   ├── main.py
│   ├── README.md
│   └── requirements.txt
└── web_interface/
    ├── Dockerfile
    ├── src/
    └── README.md
```

## Data Model

The `messages` table is created automatically from `db/init.sql`.

Important fields:

- `phone_number`: sender/receiver number
- `body`: SMS text
- `direction`: `inbound` or `outbound`
- `status`: message processing state (default: `pending`)
- `retry_count`: number of retry to process
- `error_message`: optional error details
- `created_at` / `updated_at`: timestamps

## Quick Start

### 1. Prerequisites

- Docker
- Docker Compose
- Environement variables :
    - MYSQL_PASSWORD
    - SMS_GATEWAY_IP

### 2. Start the services

From the project root:

```bash
docker compose up -d --build
```

Services started:

- MySQL on port `3306`
- FastAPI backend on port `8000`

### 3. Verify the API

Open:

- Swagger UI: `http://localhost:8000/docs`

## API Endpoints

### `POST /webhook`

Receives inbound SMS payloads from Android SMS Gateway.

Example request body:

```json
{
	"event": "sms:received",
	"payload": {
		"messageId": "abc123",
		"message": "Hello from Android",
		"phoneNumber": "+33600000000",
		"simNumber": 1,
		"receivedAt": "2026-04-12T10:30:00Z"
	}
}
```

Behavior:

- Writes a new row in `messages`
- Sets `direction = inbound`
- Sets `status = pending`

### `POST /api/messages/send`

Queues outbound SMS requests coming from the web interface.

Example request body:

```json
{
	"phoneNumber": "+33600000000",
	"message": "Message to send"
}
```

Behavior:

- Writes a new row in `messages`
- Sets `direction = outbound`
- Sets `status = pending`

## Android SMS Gateway Integration

1. Install your Android SMS Gateway app.
2. Configure its webhook URL to point to this backend (check https://github.com/capcom6/android-sms-gateway?tab=readme-ov-file#setting-up-webhooks):

```text
https://<YOUR_SERVER_IP>:8000/webhook
```

You need an SSL certificate on the webhook url, you can use a reverse proxy as caddy or NPM.

## Development Notes

- Database schema initialization is in `db/init.sql`.

## License

See `LICENSE`.