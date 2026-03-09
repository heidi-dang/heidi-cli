# OpenCode Auto-Registration

The Learning Suite is designed to be a "zero-config" provider for OpenCode.

## How it Works

1. **Discovery:** When the Suite model host is started via `heidi model serve`, it begins listening on the configured port (default 8000).
2. **Endpoint:** OpenCode is configured to poll `http://localhost:8000/v1/models`.
3. **Registration:** Every model returned by the Suite's `/v1/models` endpoint is automatically registered in OpenCode as a valid provider/model pair.

## Verification

To verify that auto-registration is possible:
1. Run `heidi model serve`.
2. Run `curl http://localhost:8000/v1/models`.
3. Ensure the JSON response contains the `data` array with your configured models.

If the discovery host is unreachable, the CLI will show an explicit error in the logs.
