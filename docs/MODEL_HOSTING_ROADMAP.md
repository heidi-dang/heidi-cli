# 🎯 Heidi CLI - Model Hosting Platform Implementation Plan

## **📋 Executive Summary**

Transform Heidi CLI into a **pure model hosting platform** that serves models to autonomous coding platforms (opencode, oh-my-opencode, Cursor, Continue, etc.) via OpenAI-compatible API.

---

## **🏗️ Architecture Overview**

```
External Platforms → Heidi CLI Model Host → Model Registry + Storage
     (Consumers)        (Provider)           (Infrastructure)
```

### **Core Components**
1. **Model Host API** - OpenAI-compatible endpoints
2. **Model Registry** - Version control and management
3. **Model Storage** - Local and cloud model storage
4. **Load Balancer** - Request routing and failover
5. **Monitoring** - Health checks and analytics

---

## **🎯 Phase 1: Core Model Hosting (Week 1-2)**

### **✅ Already Complete**
- [x] OpenAI-compatible API endpoints
- [x] Multi-model routing (OpenCode + local)
- [x] Streaming support
- [x] Basic model registry
- [x] Configuration management

### **🔧 Enhancements Needed**

#### **1. Model Discovery API**
```python
# GET /v1/models - Enhanced model listing
@app.get("/v1/models")
async def list_models():
    """Enhanced model listing with metadata"""
    return {
        "object": "list",
        "data": [
            {
                "id": "opencode-gpt-4",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai",
                "permission": [],
                "root": "https://api.opencode.ai",
                "parent": None,
                "capabilities": ["chat", "coding", "function_calling"],
                "context_length": 128000,
                "pricing": {"input": 0.03, "output": 0.06}
            }
        ]
    }
```

#### **2. Model Metadata System**
```python
# Enhanced model configuration
class ModelMetadata(BaseModel):
    id: str
    display_name: str
    description: str
    capabilities: List[str]  # ["chat", "coding", "function_calling"]
    context_length: int
    pricing: Optional[Dict[str, float]]
    provider: str  # "openai", "local", "huggingface"
    status: str  # "available", "loading", "error"
    metrics: Optional[Dict[str, Any]]  # latency, throughput, etc.
```

#### **3. Health Check Enhancements**
```python
@app.get("/health")
async def health_check():
    """Detailed health status for monitoring"""
    return {
        "status": "healthy",
        "version": "0.1.1",
        "models": {
            "total": len(manager.list_models()),
            "available": len([m for m in manager.list_models() if m.get("status") == "available"]),
            "loading": len([m for m in manager.list_models() if m.get("status") == "loading"])
        },
        "uptime": manager.uptime,
        "requests_handled": manager.metrics.total_requests,
        "avg_latency_ms": manager.metrics.avg_latency
    }
```

---

## **🔄 Phase 2: Advanced Model Management (Week 3-4)**

### **1. Model Pooling and Load Balancing**
```python
class ModelPool:
    """Manage multiple model instances for load balancing"""
    
    def __init__(self):
        self.pools: Dict[str, List[ModelInstance]] = {}
        self.round_robin: Dict[str, int] = {}
    
    async def get_instance(self, model_id: str) -> ModelInstance:
        """Get best available instance for model"""
        pool = self.pools.get(model_id, [])
        
        # Filter healthy instances
        healthy = [inst for inst in pool if inst.is_healthy()]
        
        if not healthy:
            raise ModelNotAvailableError(f"No healthy instances for {model_id}")
        
        # Round-robin selection
        idx = self.round_robin.get(model_id, 0) % len(healthy)
        instance = healthy[idx]
        self.round_robin[model_id] = idx + 1
        
        return instance
```

### **2. Model Caching and Preloading**
```python
class ModelCache:
    """Preload and cache models for faster response"""
    
    def __init__(self, max_cache_size: int = 3):
        self.cache: Dict[str, ModelInstance] = {}
        self.max_size = max_cache_size
        self.access_order: List[str] = []
    
    async def preload_model(self, model_id: str):
        """Preload model into cache"""
        if model_id not in self.cache and len(self.cache) < self.max_size:
            instance = await ModelInstance.load(model_id)
            self.cache[model_id] = instance
            self.access_order.append(model_id)
    
    async def get_cached(self, model_id: str) -> Optional[ModelInstance]:
        """Get cached model if available"""
        if model_id in self.cache:
            # Move to end (LRU)
            self.access_order.remove(model_id)
            self.access_order.append(model_id)
            return self.cache[model_id]
        return None
```

### **3. Model Metrics and Monitoring**
```python
class ModelMetrics:
    """Track model performance metrics"""
    
    def __init__(self):
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.error_rates: Dict[str, float] = defaultdict(float)
        self.last_request: Dict[str, datetime] = {}
    
    def record_request(self, model_id: str, response_time: float, success: bool):
        """Record request metrics"""
        self.request_counts[model_id] += 1
        self.response_times[model_id].append(response_time)
        self.last_request[model_id] = datetime.now()
        
        # Update error rate (rolling window)
        recent_requests = self.response_times[model_id][-100:]  # Last 100 requests
        if len(recent_requests) >= 10:
            error_count = sum(1 for _ in recent_requests if not success)
            self.error_rates[model_id] = error_count / len(recent_requests)
```

---

## **🌐 Phase 3: Multi-Tenant and Security (Week 5-6)**

### **1. API Key Management**
```python
class APIKeyManager:
    """Manage API keys for different clients"""
    
    def __init__(self):
        self.keys: Dict[str, APIKey] = {}
        self.rate_limits: Dict[str, RateLimiter] = {}
    
    def validate_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key and return client info"""
        key_data = self.keys.get(api_key)
        if key_data and key_data.is_active():
            return key_data
        return None
    
    def check_rate_limit(self, api_key: str) -> bool:
        """Check if client is within rate limits"""
        limiter = self.rate_limits.get(api_key)
        if limiter:
            return limiter.allow_request()
        return True

class APIKey(BaseModel):
    key_id: str
    name: str
    created_at: datetime
    last_used: Optional[datetime]
    rate_limit: RateLimit
    allowed_models: List[str]
    is_active: bool = True
```

### **2. Request Logging and Audit**
```python
class RequestLogger:
    """Log all requests for audit and analytics"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.logger = self._setup_logger()
    
    def log_request(self, request: ChatCompletionRequest, 
                   response: Dict[str, Any], 
                   api_key: str,
                   response_time: float):
        """Log request details"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "api_key": api_key[:8] + "...",  # Partial key for privacy
            "model": request.model,
            "request_tokens": len(str(request.messages)),
            "response_tokens": len(response.get("choices", [{}])[0].get("message", {}).get("content", "")),
            "response_time_ms": response_time * 1000,
            "success": True
        }
        
        self.logger.info(json.dumps(log_entry))
```

### **3. Model Access Control**
```python
class ModelAccessControl:
    """Control which models each API key can access"""
    
    def __init__(self):
        self.permissions: Dict[str, List[str]] = {}  # api_key -> [model_ids]
    
    def can_access_model(self, api_key: str, model_id: str) -> bool:
        """Check if API key can access specific model"""
        allowed_models = self.permissions.get(api_key, [])
        return model_id in allowed_models or "*" in allowed_models  # Wildcard access
    
    def grant_access(self, api_key: str, model_ids: List[str]):
        """Grant access to specific models"""
        self.permissions[api_key] = model_ids
```

---

## **📊 Phase 4: Analytics and Dashboard (Week 7-8)**

### **1. Usage Analytics**
```python
class UsageAnalytics:
    """Track and analyze usage patterns"""
    
    def __init__(self):
        self.daily_stats: Dict[str, DailyStats] = {}
        self.model_popularity: Dict[str, int] = defaultdict(int)
        self.client_usage: Dict[str, ClientStats] = {}
    
    def get_usage_report(self, period: str = "day") -> UsageReport:
        """Generate usage report for specified period"""
        if period == "day":
            return self._generate_daily_report()
        elif period == "week":
            return self._generate_weekly_report()
        elif period == "month":
            return self._generate_monthly_report()
    
    def get_model_leaderboard(self) -> List[ModelStats]:
        """Get most popular models"""
        return sorted(
            [{"model": model, "requests": count} for model, count in self.model_popularity.items()],
            key=lambda x: x["requests"],
            reverse=True
        )
```

### **2. Web Dashboard**
```python
# FastAPI dashboard endpoints
@app.get("/dashboard")
async def dashboard():
    """Main dashboard view"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_models": len(manager.list_models()),
        "active_models": len([m for m in manager.list_models() if m.get("status") == "available"]),
        "total_requests": analytics.get_total_requests(),
        "avg_response_time": analytics.get_avg_response_time(),
        "popular_models": analytics.get_model_leaderboard()[:5]
    })

@app.get("/api/stats")
async def get_stats():
    """API endpoint for real-time stats"""
    return {
        "models": {
            "total": len(manager.list_models()),
            "available": len([m for m in manager.list_models() if m.get("status") == "available"]),
            "loading": len([m for m in manager.list_models() if m.get("status") == "loading"])
        },
        "requests": {
            "total": analytics.get_total_requests(),
            "today": analytics.get_today_requests(),
            "avg_latency_ms": analytics.get_avg_response_time() * 1000
        },
        "models_popularity": analytics.get_model_leaderboard()
    }
```

---

## **🔧 Phase 5: Performance Optimization (Week 9-10)**

### **1. Request Batching**
```python
class BatchProcessor:
    """Batch similar requests for efficiency"""
    
    def __init__(self, batch_size: int = 8, max_wait_time: float = 0.1):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_requests: Dict[str, List[PendingRequest]] = defaultdict(list)
        self.processors: Dict[str, asyncio.Task] = {}
    
    async def add_request(self, model_id: str, request: ChatCompletionRequest) -> Dict[str, Any]:
        """Add request to batch and wait for completion"""
        future = asyncio.Future()
        self.pending_requests[model_id].append(PendingRequest(request, future))
        
        # Start processor if not running
        if model_id not in self.processors:
            self.processors[model_id] = asyncio.create_task(self._process_batch(model_id))
        
        return await future
    
    async def _process_batch(self, model_id: str):
        """Process batched requests"""
        while self.pending_requests[model_id]:
            batch = self.pending_requests[model_id][:self.batch_size]
            self.pending_requests[model_id] = self.pending_requests[model_id][self.batch_size:]
            
            # Process batch together
            try:
                responses = await self._process_batch_requests(model_id, batch)
                for req, response in zip(batch, responses):
                    req.future.set_result(response)
            except Exception as e:
                for req in batch:
                    req.future.set_exception(e)
            
            # Small delay to allow more requests to accumulate
            await asyncio.sleep(0.01)
```

### **2. Response Caching**
```python
class ResponseCache:
    """Cache identical requests for performance"""
    
    def __init__(self, max_size: int = 1000, ttl: float = 300.0):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get_cache_key(self, request: ChatCompletionRequest) -> str:
        """Generate cache key for request"""
        # Include model, messages, temperature, etc.
        key_data = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    async def get(self, request: ChatCompletionRequest) -> Optional[Dict[str, Any]]:
        """Get cached response if available"""
        key = self.get_cache_key(request)
        entry = self.cache.get(key)
        
        if entry and (datetime.now() - entry.created_at).total_seconds() < self.ttl:
            entry.hits += 1
            return entry.response
        
        return None
    
    async def set(self, request: ChatCompletionRequest, response: Dict[str, Any]):
        """Cache response"""
        key = self.get_cache_key(request)
        
        # Evict oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
            del self.cache[oldest_key]
        
        self.cache[key] = CacheEntry(
            response=response,
            created_at=datetime.now(),
            hits=0
        )
```

---

## **🚀 Implementation Timeline**

### **Week 1-2: Core Enhancements**
- [ ] Enhanced model discovery API
- [ ] Model metadata system
- [ ] Improved health checks
- [ ] Basic metrics collection

### **Week 3-4: Advanced Features**
- [ ] Model pooling and load balancing
- [ ] Model preloading and caching
- [ ] Comprehensive metrics
- [ ] Performance monitoring

### **Week 5-6: Security & Multi-Tenant**
- [ ] API key management
- [ ] Request logging and audit
- [ ] Model access control
- [ ] Rate limiting

### **Week 7-8: Analytics & Dashboard**
- [ ] Usage analytics
- [ ] Web dashboard
- [ ] Real-time monitoring
- [ ] Usage reports

### **Week 9-10: Performance**
- [ ] Request batching
- [ ] Response caching
- [ ] Memory optimization
- [ ] Load testing

---

## **📋 Success Metrics**

### **Technical Metrics**
- [ ] API response time < 500ms (95th percentile)
- [ ] 99.9% uptime
- [ ] Support 100+ concurrent requests
- [ ] Memory usage < 2GB for 10 models

### **Business Metrics**
- [ ] Serve 5+ external platforms
- [ ] Handle 10K+ requests/day
- [ ] 0% model deployment failures
- [ ] < 1 minute rollback time

---

## **🎯 Next Steps**

1. **Start Phase 1 implementation** - Enhanced model discovery and metadata
2. **Set up development environment** - Testing with external platforms
3. **Create integration examples** - opencode, Cursor, Continue
4. **Performance testing** - Load testing with concurrent requests
5. **Documentation** - Integration guides for platform developers

---

## **📞 Integration Support**

### **For Platform Developers**
- Integration guides and examples
- SDK libraries (Python, TypeScript)
- Testing environment
- Support channels

### **For Model Providers**
- Model onboarding process
- Quality evaluation
- Performance monitoring
- Revenue sharing options

---

**This implementation plan transforms Heidi CLI into a production-ready model hosting platform that can serve any autonomous coding application while maintaining focus on model management and delivery.** 🚀
