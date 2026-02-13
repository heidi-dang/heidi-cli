# Heidi Chat

A minimal web UI for the Heidi AI backend, supporting Run and Loop modes with real-time streaming.

## Features

- **Modes**: Support for single `Run` and iterative `Loop` execution.
- **Streaming**: Real-time output via Server-Sent Events (SSE).
- **History**: View and browse past runs.
- **Configuration**: Customizable backend URL and API Key.

## Prerequisites

- Node.js (v18+)
- Running Heidi Backend (default: `http://localhost:7777`)

## Setup

1.  **Install Dependencies**

    ```bash
    npm install
    ```

    *Note: Ensure you have `react`, `react-dom`, `lucide-react`, and `vite` installed.*

2.  **Run the Application**

    ```bash
    npm run dev
    ```

    The app will start at [http://localhost:3000](http://localhost:3000).

## Configuration

### Backend URL

By default, the app connects to `http://localhost:7777`.

To change this (e.g., if using a Cloudflared tunnel):
1.  Go to **Settings** (Gear icon in sidebar).
2.  Update **Heidi Base URL**.
3.  Click **Save & Connect**.

### API Key

If your Heidi backend requires authentication:
1.  Go to **Settings**.
2.  Enter your **API Key**.
3.  The key will be sent via the `X-Heidi-Key` header.
    *Note: SSE streaming might fall back to polling if the backend strictly requires headers for streaming endpoints, as standard EventSource does not support headers.*

## Troubleshooting

-   **CORS Errors**: Ensure your Heidi backend allows CORS for `http://localhost:3000`.
-   **Connection Failed**: Verify the backend is running and the URL in Settings is correct.
