# Multi-Model Host

The Model Host provides an OpenAI-compatible interface for one or more local LLMs.

## Configuration

Models are defined in the `suite.json` config file or via environment variables.

### Examples

**`suite.json`**
```json
{
  "models": [
    {
      "id": "neural-coder-7b",
      "path": "/path/to/model",
      "backend": "transformers",
      "device": "cuda"
    },
    {
      "id": "phi-3-mini",
      "path": "/path/to/phi",
      "backend": "transformers",
      "device": "cpu"
    }
  ]
}
```

## CLI Usage

- `heidi model serve`: Starts the FastAPI server.
- `heidi model status`: Shows if the server is running and which models are active.
- `heidi model stop`: Gracefully shuts down the server.

## OpenAI Compatibility

The host implements the standard V1 endpoints:

### GET `/v1/models`
Returns a list of all configured and routable models.

### POST `/v1/chat/completions`
Routes the request to the specific model requested in the `model` field.

## Error Handling

- **Invalid Model:** Returns 400 if the requested model ID is not in config.
- **Missing Path:** Returns 404 if the model path on disk is missing.
- **Port Conflict:** Serve command will fail loudly if the port is in use.
