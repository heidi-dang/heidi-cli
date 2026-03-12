from __future__ import annotations

import json
import logging
import os
import httpx
import time
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator
import psutil
from ..shared.config import ConfigLoader, ModelConfig
from .metadata import metadata_manager, ModelStatus, ModelMetrics, ModelProvider
from ..integrations.analytics import get_analytics
from ..token_tracking.models import get_token_database, TokenUsage

logger = logging.getLogger("heidi.model_host")

# Lazy imports for transformers
torch = None
transformers = None


def _lazy_imports():
    """Lazy load torch and transformers."""
    global torch, transformers
    if transformers is None:
        import torch
        import transformers

        # Fixed: Remove redundant assignment
        return torch, transformers
    return torch, transformers


class ModelManager:
    """Manages local model loading, OpenCode API, and routing with metrics."""

    def __init__(self):
        self.config = ConfigLoader.load()
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, ModelConfig] = {m.id: m for m in self.config.models}

        # Thread safety
        self._lock = threading.RLock()

        # Load model from registry
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None
        self.model_path: Optional[Path] = None

        # Token tracking
        self.token_db = get_token_database()
        self.default_session_id = str(uuid.uuid4())

        # Generation configuration
        self.generation_config = {
            "max_new_tokens": getattr(self.config, "max_new_tokens", 128),
            "temperature": getattr(self.config, "temperature", 0.7),
            "do_sample": getattr(self.config, "do_sample", True),
            "top_p": getattr(self.config, "top_p", 0.9),
            "top_k": getattr(self.config, "top_k", 50),
        }

        # Resource limits
        self.max_memory_gb = getattr(self.config, "max_memory_gb", 8)
        self.max_concurrent_requests = getattr(self.config, "max_concurrent_requests", 10)
        self._active_requests = 0

        # Security settings
        self.allowed_model_paths = getattr(
            self.config,
            "allowed_model_paths",
            [
                Path.home() / ".local" / "heidi-engine",
                Path("models"),
                Path("state/registry"),
                Path("/media/heidi/New Volume/hf-hub/merged"),
            ],
        )

        # Lazy load model only when requested
        self.model_loaded = False

        # OpenCode API client
        self.opencode_client: Optional[httpx.AsyncClient] = None
        self._init_opencode_client()

        # Metrics tracking
        self.start_time = time.time()
        self.request_count = 0
        self.total_response_time = 0.0
        self.error_count = 0

    def _init_opencode_client(self):
        """Initialize OpenCode API client if API key is configured."""
        api_key = os.environ.get("OPENCODE_API_KEY")
        if api_key:
            self.opencode_client = httpx.AsyncClient(
                base_url="https://api.opencode.ai",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60.0,
            )
            logger.info("OpenCode API client initialized")
        else:
            logger.info("OpenCode API key not found, using local models only")

    def _validate_model_path(self, model_path: Path) -> bool:
        """Validate model path for security."""
        try:
            # Resolve absolute path
            abs_path = model_path.resolve()

            # Check if path is within allowed directories
            for allowed_path in self.allowed_model_paths:
                if allowed_path.exists():
                    try:
                        if abs_path.is_relative_to(allowed_path.resolve()):
                            return True
                    except AttributeError:
                        # Fallback for older Python versions
                        if str(abs_path).startswith(str(allowed_path.resolve())):
                            return True

            logger.warning(f"Model path not in allowed directories: {abs_path}")
            return False
        except Exception as e:
            logger.error(f"Error validating model path: {e}")
            return False

    def _check_memory_usage(self) -> bool:
        """Check if memory usage is within limits."""
        try:
            memory_info = psutil.virtual_memory()
            used_gb = memory_info.used / (1024**3)

            if used_gb > self.max_memory_gb:
                logger.warning(f"Memory usage {used_gb:.2f}GB exceeds limit {self.max_memory_gb}GB")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
            return True  # Allow on error

    def _load_model_from_registry(self):
        """Load model from active_stable in registry.json."""
        if getattr(self, "model_loaded", False) and self.model is not None:
            logger.info("Model already loaded, skipping registry load")
            return

        with self._lock:
            try:
                registry_path = self.config.data_root / "registry" / "registry.json"
                if not registry_path.exists():
                    logger.warning(f"Registry not found at {registry_path}, model not loaded")
                    return

                with open(registry_path) as f:
                    registry = json.load(f)

                active_version = registry.get("active_stable")
                if not active_version:
                    logger.warning("No active_stable version in registry")
                    return

                versions = registry.get("versions", {})
                version_info = versions.get(active_version)
                if not version_info:
                    logger.warning(f"Version {active_version} not found in registry versions")
                    return

                model_path = Path(version_info.get("path", ""))
                if not model_path.exists():
                    logger.warning(f"Model path does not exist: {model_path}")
                    return

                # Security validation
                if not self._validate_model_path(model_path):
                    logger.error(f"Security validation failed for model path: {model_path}")
                    return

                # Check memory before loading
                if not self._check_memory_usage():
                    logger.error("Insufficient memory to load model")
                    return

                self.model_path = model_path
                logger.info(f"Loading model from: {model_path}")

                # Set PyTorch memory fragmentation configuration
                os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
                
                torch, transformers = _lazy_imports()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                    str(model_path),
                    trust_remote_code=True,
                    local_files_only=True,
                )

                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                if self.tokenizer.bos_token is None:
                    self.tokenizer.bos_token = "<s>"
                if self.tokenizer.eos_token is None:
                    self.tokenizer.eos_token = "</s>"

                try:
                    from transformers import BitsAndBytesConfig

                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_use_double_quant=True,
                    )
                    self.model = transformers.AutoModelForCausalLM.from_pretrained(
                        str(model_path),
                        quantization_config=quantization_config,
                        trust_remote_code=True,
                        local_files_only=True,
                        device_map="auto",
                        offload_folder="state/offload",
                        low_cpu_mem_usage=True,
                        torch_dtype=torch.float16,
                    )
                except ImportError:
                    self.model = transformers.AutoModelForCausalLM.from_pretrained(
                        str(model_path),
                        torch_dtype=torch.float16,
                        trust_remote_code=True,
                        local_files_only=True,
                        device_map="auto",
                    )

                logger.info(f"Model loaded successfully: {active_version}")
                self.model_loaded = True

            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.tokenizer = None
                self.model = None
                self.model_path = None

    def list_models(self) -> List[Dict[str, Any]]:
        """List routable models for /v1/models with enhanced metadata."""
        models = []

        # Get all models from metadata manager
        all_metadata = metadata_manager.list_models()

        for metadata in all_metadata:
            model_dict = {
                "id": metadata.id,
                "object": "model",
                "created": int(metadata.created_at.timestamp()),
                "owned_by": metadata.provider.value,
                "permission": [],
                "root": "https://api.opencode.ai"
                if metadata.provider.value == "opencode"
                else "local",
                "parent": None,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "capabilities": [cap.value for cap in metadata.capabilities],
                "context_length": metadata.context_length,
                "max_output_tokens": metadata.max_output_tokens,
                "status": metadata.status.value,
                "provider": metadata.provider.value,
                "tags": metadata.tags,
                "version": metadata.version,
            }

            # Add pricing if available
            if metadata.pricing:
                model_dict["pricing"] = {
                    "input_tokens": metadata.pricing.input_tokens,
                    "output_tokens": metadata.pricing.output_tokens,
                    "currency": metadata.pricing.currency,
                    "unit": metadata.pricing.unit,
                }

            # Add metrics if available
            if metadata.metrics:
                model_dict["metrics"] = {
                    "avg_latency_ms": metadata.metrics.avg_latency_ms,
                    "requests_per_minute": metadata.metrics.requests_per_minute,
                    "success_rate": metadata.metrics.success_rate,
                    "last_updated": metadata.metrics.last_updated.isoformat()
                    if metadata.metrics.last_updated
                    else None,
                }

            # Add enhanced metadata for HuggingFace models
            if metadata.provider == ModelProvider.LOCAL and metadata.extra_data:
                hf_data = metadata.extra_data
                model_dict["huggingface"] = {
                    "original_id": hf_data.get("original_id"),
                    "author": hf_data.get("author"),
                    "downloads": hf_data.get("downloads"),
                    "likes": hf_data.get("likes"),
                    "pipeline_tag": hf_data.get("pipeline_tag"),
                    "model_type": hf_data.get("model_type"),
                    "languages": hf_data.get("languages"),
                    "license": hf_data.get("license"),
                    "model_family": hf_data.get("model_family"),
                    "architecture": hf_data.get("architecture"),
                    "size_gb": hf_data.get("size_gb"),
                    "file_count": hf_data.get("file_count"),
                }

            models.append(model_dict)

        return models

    async def get_response(
        self, model_id: str, messages: List[Dict[str, str]], **kwargs
    ) -> Dict[str, Any]:
        """Route request to the correct model and get response with metrics."""
        start_time = time.time()
        session_id = kwargs.pop("session_id", str(uuid.uuid4()))
        user_id = kwargs.pop("user_id", "default")
        request_start_time = kwargs.pop("request_start_time", None)

        with self._lock:
            # Check concurrent request limit
            if hasattr(self, "_active_requests") and self._active_requests >= getattr(
                self, "max_concurrent_requests", 10
            ):
                logger.warning(f"Too many concurrent requests: {self._active_requests}")
                return self._fallback_response(model_id, messages, "Server overloaded")

            if not hasattr(self, "_active_requests"):
                self._active_requests = 0
            self._active_requests += 1

        # Get analytics instance
        analytics = get_analytics()

        # Calculate input tokens (rough estimate)
        input_text = " ".join([msg.get("content", "") for msg in messages])
        input_tokens = len(input_text.split()) * 1.3  # Rough token estimation

        try:
            # Check if it's an OpenCode model
            if model_id.startswith("opencode-"):
                response = await self._get_opencode_response(model_id, messages, **kwargs)

            # Check if local model is loaded
            elif self.model is None or self.tokenizer is None:
                # Fallback to placeholder response
                logger.warning("Model not loaded, using fallback response")
                response = self._fallback_response(model_id, messages)

            else:
                # Use local model
                response = await self._get_local_response(model_id, messages, **kwargs)

            # Update metrics
            response_time = time.time() - start_time
            self.total_response_time += response_time
            self._update_model_metrics(model_id, response_time, success=True)

            # Record analytics
            response_time_ms = response_time * 1000
            output_tokens = len(response["choices"][0]["message"]["content"].split()) * 1.3

            analytics.record_request(
                model_id=model_id,
                request_tokens=int(input_tokens),
                response_tokens=int(output_tokens),
                response_time_ms=response_time_ms,
                success=True,
            )

            return response

        except Exception as e:
            # Update error metrics
            self.error_count += 1
            response_time = time.time() - start_time
            self._update_model_metrics(model_id, response_time, success=False)

            # Record error analytics
            response_time_ms = response_time * 1000
            analytics.record_request(
                model_id=model_id,
                request_tokens=int(input_tokens),
                response_tokens=0,
                response_time_ms=response_time_ms,
                success=False,
                error_message=str(e),
            )

            logger.error(f"Error in get_response for {model_id}: {e}")
            raise
        finally:
            # CRITICAL: Always decrement the active requests counter
            with self._lock:
                if hasattr(self, "_active_requests"):
                    self._active_requests = max(0, self._active_requests - 1)

    def _fallback_response(self, model_id: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fallback response when model is not available."""
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        response_text = f"[Local {model_id} Response to: {prompt[:50]}...]"

        return {
            "id": f"chatcmpl-{model_id}",
            "object": "chat.completion",
            "created": 1677610602,
            "model": model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(prompt.split()) + len(response_text.split()),
            },
        }

    async def _get_opencode_response(
        self, model_id: str, messages: List[Dict[str, str]], **kwargs
    ) -> Dict[str, Any]:
        """Get response from OpenCode API."""
        if not self.opencode_client:
            raise ValueError("OpenCode API client not initialized")

        # Extract actual model name (remove opencode- prefix)
        actual_model = model_id.replace("opencode-", "")

        try:
            response = await self.opencode_client.post(
                "/v1/chat/completions",
                json={
                    "model": actual_model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 128),
                    "stop": kwargs.get("stop"),
                    "top_p": kwargs.get("top_p", 1.0),
                    "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                    "presence_penalty": kwargs.get("presence_penalty", 0.0),
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"OpenCode API error: {e}")
            raise ValueError(f"OpenCode API request failed: {e}")

    async def stream_response(
        self, model_id: str, messages: List[Dict[str, str]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from the correct model."""
        if model_id.startswith("opencode-"):
            async for chunk in self._stream_opencode_response(model_id, messages, **kwargs):
                yield chunk
        else:
            async for chunk in self._stream_local_response(model_id, messages, **kwargs):
                yield chunk

    async def _stream_opencode_response(
        self, model_id: str, messages: List[Dict[str, str]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenCode API."""
        if not self.opencode_client:
            raise ValueError("OpenCode API client not initialized")

        actual_model = model_id.replace("opencode-", "")

        try:
            async with self.opencode_client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": actual_model,
                    "messages": messages,
                    "stream": True,
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 128),
                    "stop": kwargs.get("stop"),
                    "top_p": kwargs.get("top_p", 1.0),
                    "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                    "presence_penalty": kwargs.get("presence_penalty", 0.0),
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        yield line[6:]  # Remove "data: " prefix
        except Exception as e:
            logger.error(f"OpenCode streaming error: {e}")
            raise

    async def _stream_local_response(
        self, model_id: str, messages: List[Dict[str, str]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from local model."""
        if self.model is None or self.tokenizer is None:
            # Fallback streaming response
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            response_text = f"[Local {model_id} Response to: {prompt[:50]}...]"

            chunk = {
                "id": f"chatcmpl-{model_id}",
                "object": "chat.completion.chunk",
                "created": 1677610602,
                "model": model_id,
                "choices": [
                    {"index": 0, "delta": {"content": response_text}, "finish_reason": None}
                ],
            }
            yield json.dumps(chunk)

            # Final chunk
            chunk["choices"][0]["finish_reason"] = "stop"
            yield json.dumps(chunk)
            return

        # For local models, we'll simulate streaming by generating full response first
        # then yielding it in chunks (real implementation would use model.generate() with streaming)
        full_response = await self.get_response(model_id, messages, **kwargs)
        content = full_response["choices"][0]["message"]["content"]

        # Split content into words for streaming effect
        words = content.split()
        for i, word in enumerate(words):
            chunk = {
                "id": f"chatcmpl-{model_id}",
                "object": "chat.completion.chunk",
                "created": 1677610602,
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": word + (" " if i < len(words) - 1 else "")},
                        "finish_reason": None,
                    }
                ],
            }
            yield json.dumps(chunk)

        # Final chunk
        chunk["choices"][0]["delta"] = {}
        chunk["choices"][0]["finish_reason"] = "stop"
        yield json.dumps(chunk)

    async def _get_local_response(
        self, model_id: str, messages: List[Dict[str, str]], **kwargs
    ) -> Dict[str, Any]:
        """Get response from local model with enhanced parameters."""
        try:
            # Check if model is loaded
            if self.model is None or self.tokenizer is None:
                logger.warning("Model not loaded, using fallback response")
                return self._fallback_response(model_id, messages, "Model not loaded")

            # Check memory usage
            if not self._check_memory_usage():
                logger.warning("High memory usage, using fallback response")
                return self._fallback_response(model_id, messages, "High memory usage")

            logger.info(f"Generating response for {len(messages)} messages")
            logger.info(f"Messages: {messages}")

            # Merge generation config with request parameters
            gen_config = self.generation_config.copy()
            gen_config.update({k: v for k, v in kwargs.items() if k in gen_config})

            # Extract session and user context
            session_id = kwargs.get("session_id", self.default_session_id)
            user_id = kwargs.get("user_id", "default")
            request_start_time = datetime.now()

            # Validate and fix message history (e.g. alternating roles for Mistral)
            messages = self._validate_and_fix_messages(messages)

            # Use chat template
            logger.info("Applying chat template...")
            inputs = self.tokenizer.apply_chat_template(
                messages, tokenize=True, return_tensors="pt"
            )
            
            # Fix: handle both tensor and dict-like inputs (BatchEncoding)
            from collections.abc import Mapping
            
            if isinstance(inputs, Mapping):
                input_ids = inputs.get("input_ids")
                if input_ids is not None:
                    logger.info(f"Input size: {input_ids.size()}")
                
                # Move all tensors in the mapping to the device
                device = next(self.model.parameters()).device
                logger.info(f"Model device: {device}")
                inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in inputs.items()}
            else:
                # Direct tensor input
                logger.info(f"Input size: {inputs.size() if hasattr(inputs, 'size') else 'unknown'}")
                device = next(self.model.parameters()).device
                inputs = inputs.to(device)
            
            logger.info("Moved inputs to device")

            # Generate response with supported parameters only
            gen_kwargs = {
                "max_new_tokens": kwargs.get("max_tokens", 128),
                "do_sample": True,
                "temperature": kwargs.get("temperature", 0.7),
                "pad_token_id": self.tokenizer.pad_token_id
                if self.tokenizer.pad_token_id is not None
                else self.tokenizer.eos_token_id,
            }

            top_p = kwargs.get("top_p")
            if top_p:
                gen_kwargs["top_p"] = top_p

            top_k = kwargs.get("top_k")
            if top_k:
                gen_kwargs["top_k"] = top_k

            logger.info(f"Generating with config: {gen_kwargs}")
            if isinstance(inputs, Mapping):
                outputs = self.model.generate(**inputs, **gen_kwargs)
            else:
                outputs = self.model.generate(inputs, **gen_kwargs)
            logger.info(f"Generated output shape: {outputs.shape}")

            # Decode only the new tokens (skip input)
            from collections.abc import Mapping
            if isinstance(inputs, Mapping):
                input_length = inputs["input_ids"].shape[1]
            else:
                input_length = inputs.shape[1]
                
            response_tokens = outputs[0][input_length:]
            response_text = self.tokenizer.decode(response_tokens, skip_special_tokens=True)

            # Create response
            response = {
                "id": f"chatcmpl-{model_id}",
                "object": "chat.completion",
                "created": 1677610602,
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": input_length,
                    "completion_tokens": len(response_tokens),
                    "total_tokens": input_length + len(response_tokens),
                },
            }

            # Record token usage
            self._record_token_usage(
                model_id=model_id,
                session_id=session_id,
                user_id=user_id,
                prompt_tokens=input_length,
                completion_tokens=len(response_tokens),
                total_tokens=input_length + len(response_tokens),
                request_type="chat_completion",
                metadata={
                    "request_start_time": request_start_time.isoformat()
                    if request_start_time
                    else None,
                    "generation_config": gen_config,
                    "model_path": str(self.model_path) if self.model_path else None,
                },
            )

            return response

        except Exception as e:
            import traceback

            logger.error(f"Error during local model inference: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._fallback_response(model_id, messages)

    def _update_model_metrics(self, model_id: str, response_time: float, success: bool):
        """Update metrics for a specific model"""
        try:
            metadata = metadata_manager.get_metadata(model_id)
            if metadata:
                # Calculate new metrics
                total_requests = self.request_count
                avg_response_time = self.total_response_time / total_requests
                success_rate = (total_requests - self.error_count) / total_requests

                # Update metrics
                metrics = ModelMetrics(
                    avg_latency_ms=avg_response_time * 1000,
                    requests_per_minute=total_requests / ((time.time() - self.start_time) / 60),
                    success_rate=success_rate,
                    last_updated=datetime.now(),
                )

                metadata_manager.update_model_metrics(model_id, metrics)
        except Exception as e:
            logger.error(f"Failed to update metrics for {model_id}: {e}")

    @property
    def uptime(self) -> float:
        """Get manager uptime in seconds"""
        return time.time() - self.start_time

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get overall manager metrics"""
        return {
            "total_requests": self.request_count,
            "avg_latency_ms": (self.total_response_time / self.request_count * 1000)
            if self.request_count > 0
            else 0,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "uptime_seconds": self.uptime,
            "memory_used_gb": psutil.virtual_memory().used / (1024**3),
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "memory_percent": psutil.virtual_memory().percent,
            "active_requests": self._active_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
            "model_loaded": self.model is not None,
            "model_path": str(self.model_path) if self.model_path else None,
            "session_id": self.default_session_id,
        }

    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count using simple heuristics when tokenizer unavailable."""
        if not text:
            return 0

        # Simple heuristic: average token is ~4 characters
        # Add some buffer for special tokens
        estimated_tokens = len(text) // 4 + len(text.split()) // 2
        return max(1, estimated_tokens)

    def _fallback_response(
        self, model_id: str, messages: List[Dict[str, str]], error_msg: str = ""
    ) -> Dict[str, Any]:
        """Fallback response when model is not available."""
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        response_text = f"[Local {model_id} Response to: {prompt[:50]}...]"
        if error_msg:
            response_text = f"[Model unavailable: {error_msg}]"

        # Proper token counting
        prompt_tokens = self._estimate_token_count(prompt)
        completion_tokens = self._estimate_token_count(response_text)

        return {
            "id": f"chatcmpl-{model_id}",
            "object": "chat.completion",
            "created": 1677610602,
            "model": model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    def unload_model(self):
        """Unload model and free memory."""
        with self._lock:
            try:
                if self.model is not None:
                    # Move model to CPU first
                    if hasattr(self.model, "cpu"):
                        self.model.cpu()

                    # Clear references
                    del self.model
                    self.model = None

                if self.tokenizer is not None:
                    del self.tokenizer
                    self.tokenizer = None

                self.model_path = None

                # Force garbage collection
                import gc

                gc.collect()

                # Clear CUDA cache if available
                try:
                    torch = _lazy_imports()[0]
                    if torch and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass

                logger.info("Model unloaded successfully")

            except Exception as e:
                logger.error(f"Error unloading model: {e}")

    def reload_model(self):
        """Reload model from registry."""
        self.unload_model()
        self._load_model_from_registry()

    def _record_token_usage(
        self,
        model_id: str,
        session_id: str,
        user_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        request_type: str = "chat_completion",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record token usage to database."""
        try:
            # Get cost configuration
            cost_config = self.token_db.get_cost_config("local", model_id)

            # Calculate cost
            if cost_config:
                cost_usd = cost_config.calculate_cost(prompt_tokens, completion_tokens)
            else:
                # Default cost estimation for local models
                cost_usd = 0.0  # Free for local models

            # Create usage record
            usage = TokenUsage(
                model_id=model_id,
                session_id=session_id,
                user_id=user_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                request_type=request_type,
                model_provider="local",
                cost_usd=cost_usd,
                metadata=metadata,
            )

            # Save to database
            self.token_db.record_usage(usage)

            logger.debug(f"Recorded token usage: {total_tokens} tokens for {model_id}")

        except Exception as e:
            logger.error(f"Failed to record token usage: {e}")

    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource usage status."""
        try:
            memory = psutil.virtual_memory()
            return {
                "memory_used_gb": memory.used / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "memory_percent": memory.percent,
                "active_requests": self._active_requests,
                "max_concurrent_requests": self.max_concurrent_requests,
                "model_loaded": self.model is not None,
                "model_path": str(self.model_path) if self.model_path else None,
                "session_id": self.default_session_id,
            }
        except Exception as e:
            logger.error(f"Error getting resource status: {e}")
            return {"error": str(e)}

    def _validate_and_fix_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Validate and fix message history to ensure alternating roles (user/assistant).
        Mistral and many other models require alternating roles.
        """
        if not messages:
            return messages

        fixed_messages = []
        last_role = None

        # System message is optional and must be first
        start_idx = 0
        if messages[0]["role"] == "system":
            fixed_messages.append(messages[0].copy())
            start_idx = 1

        for i in range(start_idx, len(messages)):
            msg = messages[i].copy()
            role = msg["role"]
            content = msg["content"]

            if role == last_role:
                # Merge consecutive messages with the same role
                if fixed_messages:
                    fixed_messages[-1]["content"] += "\n\n" + content
                else:
                    fixed_messages.append(msg)
            else:
                # Basic alternating logic
                if last_role is None and role != "user":
                    # First message after system must be user
                    msg["role"] = "user"
                    fixed_messages.append(msg)
                else:
                    fixed_messages.append(msg)
            
            last_role = fixed_messages[-1]["role"]

        # Ensure alternating user/assistant for Mistral
        final_messages = []
        if fixed_messages and fixed_messages[0]["role"] == "system":
            final_messages.append(fixed_messages[0])
            fixed_messages = fixed_messages[1:]
        
        expecting_role = "user"
        for msg in fixed_messages:
            if msg["role"] == expecting_role:
                final_messages.append(msg)
                expecting_role = "assistant" if expecting_role == "user" else "user"
            else:
                # Merge if roles don't alternate as expected
                if final_messages and final_messages[-1]["role"] != "system":
                    final_messages[-1]["content"] += "\n\n" + msg["content"]
                else:
                    # Force user role if we were expecting user but got assistant first
                    msg["role"] = "user"
                    final_messages.append(msg)
                    expecting_role = "assistant"
                    
        return final_messages


# Global manager instance
manager = ModelManager()
