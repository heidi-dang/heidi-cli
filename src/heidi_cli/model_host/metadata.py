from __future__ import annotations

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class ModelProvider(str, Enum):
    OPENAI = "openai"
    OPENCODE = "opencode"
    LOCAL = "local"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    CHAT = "chat"
    CODING = "coding"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    VISION = "vision"
    EMBEDDINGS = "embeddings"


class ModelStatus(str, Enum):
    AVAILABLE = "available"
    LOADING = "loading"
    ERROR = "error"
    OFFLINE = "offline"


class ModelPricing(BaseModel):
    input_tokens: Optional[float] = None
    output_tokens: Optional[float] = None
    currency: str = "USD"
    unit: str = "per_1k_tokens"


class ModelMetrics(BaseModel):
    avg_latency_ms: Optional[float] = None
    requests_per_minute: Optional[float] = None
    success_rate: Optional[float] = None
    last_updated: Optional[datetime] = None


class ModelMetadata(BaseModel):
    id: str
    display_name: str
    description: str
    provider: ModelProvider
    capabilities: List[ModelCapability]
    context_length: int
    max_output_tokens: int
    pricing: Optional[ModelPricing] = None
    status: ModelStatus = ModelStatus.AVAILABLE
    metrics: Optional[ModelMetrics] = None
    tags: List[str] = []
    version: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Predefined model metadata for common models
MODEL_CATALOG = {
    # OpenCode Models
    "opencode-gpt-4": ModelMetadata(
        id="opencode-gpt-4",
        display_name="GPT-4 (OpenCode)",
        description="OpenCode's GPT-4 model for general purpose tasks",
        provider=ModelProvider.OPENCODE,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODING, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING],
        context_length=128000,
        max_output_tokens=4096,
        pricing=ModelPricing(input_tokens=0.03, output_tokens=0.06),
        tags=["general", "coding", "large"],
        version="1.0",
        created_at=datetime.now(),
        updated_at=datetime.now()
    ),
    
    "opencode-gpt-4-turbo": ModelMetadata(
        id="opencode-gpt-4-turbo",
        display_name="GPT-4 Turbo (OpenCode)",
        description="Faster version of GPT-4 with recent knowledge",
        provider=ModelProvider.OPENCODE,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODING, ModelCapability.FUNCTION_CALLING, ModelCapability.STREAMING],
        context_length=128000,
        max_output_tokens=4096,
        pricing=ModelPricing(input_tokens=0.01, output_tokens=0.03),
        tags=["general", "coding", "fast", "recent"],
        version="1.0",
        created_at=datetime.now(),
        updated_at=datetime.now()
    ),
    
    "opencode-claude-3-opus": ModelMetadata(
        id="opencode-claude-3-opus",
        display_name="Claude 3 Opus (OpenCode)",
        description="Anthropic's most capable model for complex tasks",
        provider=ModelProvider.OPENCODE,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODING, ModelCapability.STREAMING],
        context_length=200000,
        max_output_tokens=4096,
        pricing=ModelPricing(input_tokens=0.015, output_tokens=0.075),
        tags=["reasoning", "coding", "large", "safe"],
        version="3.0",
        created_at=datetime.now(),
        updated_at=datetime.now()
    ),
    
    "opencode-claude-3-sonnet": ModelMetadata(
        id="opencode-claude-3-sonnet",
        display_name="Claude 3 Sonnet (OpenCode)",
        description="Balanced model for performance and speed",
        provider=ModelProvider.OPENCODE,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODING, ModelCapability.STREAMING],
        context_length=200000,
        max_output_tokens=4096,
        pricing=ModelPricing(input_tokens=0.003, output_tokens=0.015),
        tags=["balanced", "coding", "safe"],
        version="3.0",
        created_at=datetime.now(),
        updated_at=datetime.now()
    ),
    
    "opencode-claude-3-haiku": ModelMetadata(
        id="opencode-claude-3-haiku",
        display_name="Claude 3 Haiku (OpenCode)",
        description="Fast and efficient model for simple tasks",
        provider=ModelProvider.OPENCODE,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODING, ModelCapability.STREAMING],
        context_length=200000,
        max_output_tokens=4096,
        pricing=ModelPricing(input_tokens=0.00025, output_tokens=0.00125),
        tags=["fast", "efficient", "simple"],
        version="3.0",
        created_at=datetime.now(),
        updated_at=datetime.now()
    ),
}


class MetadataManager:
    """Manage model metadata for the hosting platform"""
    
    def __init__(self):
        self.custom_models: Dict[str, ModelMetadata] = {}
        self._load_custom_models()
    
    def _load_custom_models(self):
        """Load custom model metadata from registry"""
        try:
            from ..registry.manager import model_registry
            registry = model_registry.load_registry()
            
            for version_id, version_info in registry.get("versions", {}).items():
                # Create metadata for registry models
                metadata = ModelMetadata(
                    id=version_id,
                    display_name=version_id,
                    description=f"Local model version {version_id}",
                    provider=ModelProvider.LOCAL,
                    capabilities=[ModelCapability.CHAT, ModelCapability.CODING, ModelCapability.STREAMING],
                    context_length=4096,  # Default, should be updated from model config
                    max_output_tokens=2048,
                    status=ModelStatus.AVAILABLE if version_info.get("channel") == "stable" else ModelStatus.LOADING,
                    tags=[version_info.get("channel", "local")],
                    version=version_id,
                    created_at=datetime.fromisoformat(version_info.get("registered_at", datetime.now().isoformat())),
                    updated_at=datetime.now()
                )
                self.custom_models[version_id] = metadata
                
        except Exception as e:
            # Registry might not be initialized yet
            pass
    
    def get_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Get metadata for a specific model"""
        # Check catalog first
        if model_id in MODEL_CATALOG:
            return MODEL_CATALOG[model_id]
        
        # Check custom models
        if model_id in self.custom_models:
            return self.custom_models[model_id]
        
        return None
    
    def list_models(self, provider: Optional[ModelProvider] = None, 
                   capability: Optional[ModelCapability] = None,
                   status: Optional[ModelStatus] = None) -> List[ModelMetadata]:
        """List models with optional filtering"""
        all_models = {**MODEL_CATALOG, **self.custom_models}
        
        filtered_models = []
        for model in all_models.values():
            # Filter by provider
            if provider and model.provider != provider:
                continue
            
            # Filter by capability
            if capability and capability not in model.capabilities:
                continue
            
            # Filter by status
            if status and model.status != status:
                continue
            
            filtered_models.append(model)
        
        return filtered_models
    
    def add_custom_model(self, metadata: ModelMetadata):
        """Add a custom model to the catalog"""
        self.custom_models[metadata.id] = metadata
    
    def update_model_status(self, model_id: str, status: ModelStatus):
        """Update model status"""
        metadata = self.get_metadata(model_id)
        if metadata:
            metadata.status = status
            metadata.updated_at = datetime.now()
    
    def update_model_metrics(self, model_id: str, metrics: ModelMetrics):
        """Update model metrics"""
        metadata = self.get_metadata(model_id)
        if metadata:
            metadata.metrics = metrics
            metadata.updated_at = datetime.now()


# Global metadata manager
metadata_manager = MetadataManager()
