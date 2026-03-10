from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    from huggingface_hub.utils import RepositoryNotFoundError, RevisionNotFoundError
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    HfApi = None
    hf_hub_download = None
    snapshot_download = None
    RepositoryNotFoundError = None
    RevisionNotFoundError = None

logger = logging.getLogger("heidi.huggingface")


class HuggingFaceIntegration:
    """Integration with HuggingFace Hub for model discovery and download."""
    
    def __init__(self, token: Optional[str] = None):
        if not HUGGINGFACE_AVAILABLE:
            raise ImportError(
                "huggingface_hub is required for HuggingFace integration. "
                "Install with: pip install huggingface_hub>=0.20.0"
            )
        
        self.api = HfApi(token=token)
        self.cache_dir = Path.home() / ".heidi" / "models" / "huggingface"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if token is available
        if not token:
            # Try to get token from environment
            import os
            token = os.environ.get("HUGGINGFACE_TOKEN")
            if token:
                self.api = HfApi(token=token)
                logger.info("Using HuggingFace token from environment")
    
    async def search_models(self, query: str, task_filter: str = "text-generation", limit: int = 20) -> List[Dict[str, Any]]:
        """Search models on HuggingFace Hub."""
        try:
            models = []
            
            # Search models without ModelFilter (newer API compatibility)
            for model_info in self.api.list_models(
                search=query, 
                limit=limit,
                sort="downloads"
            ):
                # Filter for relevant models manually
                if model_info.pipeline_tag and model_info.pipeline_tag != task_filter:
                    continue
                
                # Filter for relevant tags (more permissive)
                relevant_tags = ["chat", "coding", "instruct", "chatglm", "qwen", "mistral", "llama", "text-generation", "conversational"]
                if not any(tag in model_info.tags for tag in relevant_tags):
                    continue
                
                models.append({
                    "id": model_info.id,
                    "author": model_info.author,
                    "downloads": model_info.downloads,
                    "likes": model_info.likes,
                    "created_at": model_info.created_at.isoformat() if model_info.created_at else None,
                    "tags": model_info.tags,
                    "pipeline_tag": model_info.pipeline_tag,
                    "modelId": model_info.id,
                    "last_modified": model_info.last_modified.isoformat() if model_info.last_modified else None
                })
                
                if len(models) >= limit:
                    break
            
            return models
            
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            raise
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific model."""
        try:
            model_info = self.api.model_info(model_id)
            
            # Extract relevant information with compatibility for different versions
            info = {
                "id": model_info.id,
                "author": getattr(model_info, 'author', 'Unknown'),
                "description": getattr(model_info, 'description', '') or getattr(model_info.cardData, 'description', '') if hasattr(model_info, 'cardData') else '',
                "tags": getattr(model_info, 'tags', []),
                "pipeline_tag": getattr(model_info, 'pipeline_tag', 'text-generation'),
                "downloads": getattr(model_info, 'downloads', 0),
                "likes": getattr(model_info, 'likes', 0),
                "created_at": getattr(model_info, 'created_at', None),
                "last_modified": getattr(model_info, 'last_modified', None),
                "model_card": getattr(model_info, 'cardData', {}) if hasattr(model_info, 'cardData') else {},
                "config": getattr(model_info, 'config', {}) if hasattr(model_info, 'config') else {},
                "siblings": getattr(model_info, 'siblings', []) if hasattr(model_info, 'siblings') else []
            }
            
            # Format dates
            if info["created_at"]:
                info["created_at"] = info["created_at"].isoformat()
            if info["last_modified"]:
                info["last_modified"] = info["last_modified"].isoformat()
            
            # Extract useful information from tags
            info["capabilities"] = []
            info["context_length"] = None
            info["model_type"] = None
            info["languages"] = []
            
            for tag in info["tags"]:
                if tag in ["chat", "instruct", "chatglm"]:
                    info["capabilities"].append("chat")
                if tag in ["coding", "code", "python", "javascript"]:
                    info["capabilities"].append("coding")
                if tag.startswith("context-length-"):
                    try:
                        info["context_length"] = int(tag.split("-")[-1])
                    except (ValueError, IndexError):
                        pass
                if tag in ["7b", "13b", "70b", "1.8b", "3b", "30b"]:
                    info["model_type"] = tag
                if tag in ["english", "chinese", "french", "german", "spanish"]:
                    info["languages"].append(tag)
            
            # Extract context length from config if available
            if not info["context_length"] and info["config"]:
                if "max_position_embeddings" in info["config"]:
                    info["context_length"] = info["config"]["max_position_embeddings"]
                elif "model_max_length" in info["config"]:
                    info["context_length"] = info["config"]["model_max_length"]
            
            return info
            
        except Exception as e:
            # Provide user-friendly error messages
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg or "repository not found" in error_msg:
                logger.error(f"Model not found: {model_id}")
                raise ValueError(f"❌ Model '{model_id}' not found on HuggingFace Hub. Please check the model name and try again.")
            elif "401" in error_msg or "unauthorized" in error_msg or "invalid username or password" in error_msg:
                logger.error(f"Authentication failed for model: {model_id}")
                raise ValueError(f"❌ Model '{model_id}' requires authentication or is private. Please check if you have access to this model.")
            elif "403" in error_msg or "forbidden" in error_msg:
                logger.error(f"Access forbidden for model: {model_id}")
                raise ValueError(f"❌ Access to model '{model_id}' is forbidden. This may be a gated model requiring approval.")
            else:
                logger.error(f"Error getting model info for {model_id}: {e}")
                raise ValueError(f"❌ Failed to get model info for '{model_id}'. Please check your internet connection and try again.")
    
    async def download_model(self, model_id: str, force_download: bool = False) -> Dict[str, Any]:
        """Download a model from HuggingFace Hub."""
        try:
            # Create model directory
            safe_model_id = model_id.replace("/", "_").replace("\\", "_")
            model_dir = self.cache_dir / safe_model_id
            model_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading model {model_id} to {model_dir}")
            
            # Get model info first
            model_info = await self.get_model_info(model_id)
            
            # Download the model using snapshot_download for better reliability
            downloaded_files = []
            
            try:
                # Try snapshot_download first (more reliable for large models)
                downloaded_path = snapshot_download(
                    repo_id=model_id,
                    cache_dir=model_dir,
                    force_download=force_download,
                    allow_patterns=["*.json", "*.bin", "*.safetensors", "*.model"],
                    ignore_patterns=["*.git*", "*.md"]
                )
                downloaded_files = list(Path(downloaded_path).rglob("*"))
                downloaded_files = [f for f in downloaded_files if f.is_file()]
                
            except Exception as e:
                logger.warning(f"Snapshot download failed, trying individual files: {e}")
                
                # Fallback to individual file downloads
                essential_files = [
                    "config.json",
                    "tokenizer.json",
                    "vocab.json",
                    "special_tokens_map.json"
                ]
                
                # Try to download model weights
                weight_files = [
                    "pytorch_model.bin",
                    "model.safetensors",
                    "model.bin"
                ]
                
                all_files = essential_files + weight_files
                
                for filename in all_files:
                    try:
                        file_path = hf_hub_download(
                            repo_id=model_id,
                            filename=filename,
                            cache_dir=model_dir,
                            force_download=force_download
                        )
                        downloaded_files.append(Path(file_path))
                    except Exception as e:
                        logger.debug(f"Could not download {filename}: {e}")
                        continue
            
            # Calculate total size
            total_size = sum(f.stat().st_size for f in downloaded_files if f.exists())
            
            # Create metadata
            metadata = {
                "model_id": model_id,
                "safe_id": safe_model_id,
                "downloaded_at": datetime.now().isoformat(),
                "local_path": str(model_dir),
                "files": [str(f.relative_to(model_dir)) for f in downloaded_files],
                "file_count": len(downloaded_files),
                "size_bytes": total_size,
                "size_gb": round(total_size / (1024**3), 2)
            }
            
            # Save metadata
            metadata_file = model_dir / "heidi_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Successfully downloaded {model_id}: {len(downloaded_files)} files, {metadata['size_gb']} GB")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to download model {model_id}: {e}")
            raise
    
    async def auto_configure_model(self, model_id: str, model_dir: Path) -> Dict[str, Any]:
        """Automatically configure model based on HuggingFace metadata."""
        try:
            # Load model info
            model_info = await self.get_model_info(model_id)
            
            # Determine optimal configuration
            config = {
                "id": model_id.replace("/", "_").replace("\\", "_"),
                "path": str(model_dir),
                "backend": "transformers",
                "device": "auto",
                "precision": "auto",
                "source": "huggingface",
                "original_id": model_id,
                "downloaded_at": datetime.now().isoformat()
            }
            
            # Enhanced context length detection
            if model_info.get("context_length"):
                config["max_context"] = model_info["context_length"]
            else:
                # Extract from model tags
                tags = model_info.get("tags", [])
                for tag in tags:
                    if tag.startswith("context-length-"):
                        try:
                            config["max_context"] = int(tag.split("-")[-1])
                            break
                        except (ValueError, IndexError):
                            pass
                
                # Default context lengths by model size
                if "max_context" not in config:
                    model_id_lower = model_id.lower()
                    if "7b" in model_id_lower:
                        config["max_context"] = 4096
                    elif "13b" in model_id_lower:
                        config["max_context"] = 8192
                    elif "70b" in model_id_lower:
                        config["max_context"] = 16384
                    elif "1.8b" in model_id_lower or "3b" in model_id_lower:
                        config["max_context"] = 2048
                    else:
                        config["max_context"] = 4096
            
            # Set max tokens (half of context length, reasonable max)
            config["max_tokens"] = min(config["max_context"] // 2, 2048)
            
            # Enhanced capability detection
            capabilities = ["chat", "streaming"]
            
            # Check for coding capabilities
            coding_indicators = ["coding", "code", "python", "javascript", "cpp", "java", "rust", "go"]
            if any(indicator in model_info.get("tags", []) for indicator in coding_indicators):
                capabilities.append("coding")
            
            # Check for function calling
            function_calling_indicators = ["function-calling", "tool", "agent", "tool-calling"]
            if any(indicator in model_info.get("tags", []) for indicator in function_calling_indicators):
                capabilities.append("function_calling")
            
            # Check for vision capabilities
            vision_indicators = ["vision", "image", "multimodal", "clip", "vit"]
            if any(indicator in model_info.get("tags", []) for indicator in vision_indicators):
                capabilities.append("vision")
            
            # Check for embeddings
            embedding_indicators = ["embedding", "sentence-transformers", "bert", "roberta"]
            if any(indicator in model_info.get("tags", []) for indicator in embedding_indicators):
                capabilities.append("embeddings")
            
            config["capabilities"] = capabilities
            
            # Enhanced metadata extraction
            config["display_name"] = model_info.get("id", model_id)
            config["description"] = model_info.get("description", f"HuggingFace model: {model_id}")
            config["author"] = model_info.get("author", "Unknown")
            config["downloads"] = model_info.get("downloads", 0)
            config["likes"] = model_info.get("likes", 0)
            config["tags"] = model_info.get("tags", [])
            config["pipeline_tag"] = model_info.get("pipeline_tag", "text-generation")
            
            # Extract model type from tags
            model_type = None
            tags = model_info.get("tags", [])
            for tag in tags:
                if tag in ["7b", "13b", "70b", "1.8b", "3b", "30b", "1b", "6b"]:
                    model_type = tag
                    break
            config["model_type"] = model_type
            
            # Extract languages
            languages = []
            language_tags = ["english", "chinese", "french", "german", "spanish", "italian", "portuguese", "russian", "japanese", "korean"]
            for tag in tags:
                if tag in language_tags:
                    languages.append(tag)
            config["languages"] = languages
            
            # Extract license information
            license_info = None
            for tag in tags:
                if tag.startswith("license:"):
                    license_info = tag.split(":", 1)[1]
                    break
            config["license"] = license_info
            
            # Extract model family
            model_family = None
            family_indicators = ["gpt", "bert", "roberta", "t5", "llama", "mistral", "claude", "qwen", "falcon", "mpt"]
            for indicator in family_indicators:
                if indicator in model_id.lower():
                    model_family = indicator
                    break
            config["model_family"] = model_family
            
            # Extract architecture information
            architecture = None
            if "config" in model_info and model_info["config"]:
                config_data = model_info["config"]
                if isinstance(config_data, dict):
                    if "architectures" in config_data:
                        arch_data = config_data["architectures"]
                        if isinstance(arch_data, list):
                            architecture = arch_data[0] if arch_data else None
                        elif isinstance(arch_data, dict):
                            architecture = list(arch_data.keys())[0] if arch_data else None
                    elif "model_type" in config_data:
                        architecture = config_data["model_type"]
            config["architecture"] = architecture
            
            # Determine device requirements
            if model_type:
                if model_type in ["70b", "30b"]:
                    config["device"] = "cuda"  # Require GPU for large models
                    config["precision"] = "fp16"  # Use half precision
                elif model_type in ["13b", "7b"]:
                    config["device"] = "auto"
                    config["precision"] = "auto"
                else:
                    config["device"] = "auto"
                    config["precision"] = "auto"
            
            return config
            
        except Exception as e:
            logger.error(f"Error auto-configuring model {model_id}: {e}")
            raise
    
    def list_local_models(self) -> List[Dict[str, Any]]:
        """List all locally downloaded HuggingFace models."""
        local_models = []
        
        if not self.cache_dir.exists():
            return local_models
        
        for model_dir in self.cache_dir.iterdir():
            if model_dir.is_dir():
                metadata_file = model_dir / "heidi_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                        local_models.append(metadata)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Error reading metadata for {model_dir.name}: {e}")
                        # Try to create basic metadata from directory structure
                        try:
                            basic_metadata = {
                                "model_id": model_dir.name.replace("_", "/"),
                                "safe_id": model_dir.name,
                                "downloaded_at": "Unknown",
                                "local_path": str(model_dir),
                                "files": [],
                                "file_count": 0,
                                "size_bytes": 0,
                                "size_gb": 0.0
                            }
                            local_models.append(basic_metadata)
                        except Exception:
                            continue
        
        return sorted(local_models, key=lambda x: x.get("downloaded_at", ""), reverse=True)
    
    def get_local_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a locally downloaded model."""
        safe_model_id = model_id.replace("/", "_").replace("\\", "_")
        metadata_file = self.cache_dir / safe_model_id / "heidi_metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading metadata for {model_id}: {e}")
        
        return None
    
    async def remove_model(self, model_id: str) -> bool:
        """Remove a locally downloaded model."""
        try:
            safe_model_id = model_id.replace("/", "_").replace("\\", "_")
            model_dir = self.cache_dir / safe_model_id
            
            if model_dir.exists():
                import shutil
                shutil.rmtree(model_dir)
                logger.info(f"Removed model {model_id} from local storage")
                return True
            else:
                logger.warning(f"Model {model_id} not found in local storage")
                return False
                
        except Exception as e:
            logger.error(f"Error removing model {model_id}: {e}")
            return False


# Global instance - created lazily when needed
huggingface_integration = None

def get_huggingface_integration():
    """Get the HuggingFace integration instance, creating it if needed."""
    global huggingface_integration
    if huggingface_integration is None:
        huggingface_integration = HuggingFaceIntegration()
    return huggingface_integration
