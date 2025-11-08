# Sheratan Guard

Policy engine, PII detection, audit logging, and rate limiting for security and compliance.

## Features

### Policy Engine
- Configurable policy rules via YAML
- Actions: ALLOW, DENY, REDACT, WARN
- Custom condition evaluation
- Dynamic policy loading from configuration files

### PII Detection
- Detects common PII types:
  - Email addresses
  - Phone numbers
  - Social Security Numbers
  - Credit card numbers
  - IP addresses
- Automatic redaction
- Detailed scanning reports

### Blocklists
- YAML-based blocklist configuration
- Multiple blocklists (spam, offensive, suspicious domains, etc.)
- Case-insensitive matching
- Easy to extend and customize

### Rate Limiting
- Per-client rate limiting (based on IP address)
- Per-endpoint configuration
- Minute and hour-based limits
- In-memory tracking with automatic cleanup
- Response headers with limit information

### Audit Logging
- Structured event logging
- Compliance tracking
- Security monitoring
- Separate audit log file
- Multiple event types (document ingest, search, policy violations, PII detection, etc.)

### Middleware Integration
- FastAPI middleware for easy integration
- Automatic guard checks on all requests
- PII scrubbing in request/response
- Rate limit enforcement
- Policy evaluation

## Environment Variables

- `GUARD_ENABLED` - Enable guard features (default: true)
- `PII_DETECTION_ENABLED` - Enable PII detection (default: true)
- `GUARD_CONFIG_DIR` - Directory containing YAML config files (default: /etc/sheratan/guard)

## Configuration

### Directory Structure

```
/etc/sheratan/guard/
  ├── policies.yaml      # Policy rules
  ├── blocklists.yaml    # Content blocklists
  └── ratelimits.yaml    # Rate limit configuration
```

Example configuration files are provided in `config-examples/`.

### Policy Configuration (policies.yaml)

```yaml
policies:
  - name: no_empty_content
    description: Reject empty content
    action: deny
    conditions:
      - field: content
        operator: empty
  
  - name: content_size_limit
    description: Reject oversized content
    action: deny
    conditions:
      - field: content_length
        operator: greater_than
        value: 10000000
```

**Available operators:** `empty`, `greater_than`, `contains`, `equals`
**Available actions:** `allow`, `deny`, `warn`, `redact`

### Blocklist Configuration (blocklists.yaml)

```yaml
blocklists:
  spam_keywords:
    - viagra
    - casino
    - lottery
  
  suspicious_domains:
    - malicious-site.com
    - spam-domain.net
```

### Rate Limit Configuration (ratelimits.yaml)

```yaml
rate_limits:
  global:
    requests_per_minute: 100
    requests_per_hour: 1000
  
  /ingest:
    requests_per_minute: 10
    requests_per_hour: 100
```

## Usage

### Basic PII Detection

```python
from sheratan_guard import PIIDetector

detector = PIIDetector()

text = "Contact me at john@example.com or 555-123-4567"

# Detect PII
pii = detector.detect(text)
# Returns: [{"type": "email", ...}, {"type": "phone", ...}]

# Redact PII
redacted = detector.redact(text)
# Returns: "Contact me at [REDACTED] or [REDACTED]"

# Full scan
report = detector.scan_and_report(text)
# Returns: {"has_pii": true, "pii_count": 2, ...}
```

### Policy Engine

```python
from sheratan_guard import PolicyEngine, PolicyAction

engine = PolicyEngine()

# Add custom rule
engine.add_rule(
    name="no_spam",
    condition=lambda ctx: "spam" in ctx.get("content", "").lower(),
    action=PolicyAction.DENY,
    message="Spam content not allowed"
)

# Evaluate
result = engine.evaluate({"content": "Some text"})
# Returns: {"decision": "allow", "rules_triggered": [], "messages": []}
```

### Configuration Loading

```python
from sheratan_guard import GuardConfig

# Load from default directory or GUARD_CONFIG_DIR env var
config = GuardConfig()

# Or specify custom directory
config = GuardConfig(config_dir="/path/to/config")

# Get policies
policies = config.get_policies()

# Get blocklist
spam_list = config.get_blocklist("spam_keywords")

# Check if text is blocked
is_blocked = config.is_blocked("some text", "spam_keywords")

# Get rate limits for endpoint
limits = config.get_rate_limit("/ingest")
```

### Rate Limiting

```python
from sheratan_guard import RateLimiter

limiter = RateLimiter()

# Check if request is allowed
allowed, reason = limiter.is_allowed(
    client_id="user123",
    endpoint="/api/search",
    requests_per_minute=60,
    requests_per_hour=600
)

if not allowed:
    print(f"Rate limit exceeded: {reason}")

# Get usage statistics
usage = limiter.get_usage("user123", "/api/search")
print(f"Requests in last minute: {usage['requests_last_minute']}")
```

### Audit Logging

```python
from sheratan_guard import AuditLogger, AuditEventType

audit = AuditLogger()

# Log document ingest
audit.log_document_ingest(
    document_id="doc123",
    user_id="user456",
    success=True
)

# Log search
audit.log_search(
    query="search term",
    user_id="user456",
    results_count=10
)

# Log policy violation
audit.log_policy_violation(
    policy_name="no_spam",
    user_id="user456"
)

# Log PII detection
audit.log_pii_detection(
    pii_types=["email", "phone"],
    user_id="user456"
)
```

### Middleware Integration (FastAPI)

```python
from fastapi import FastAPI
from sheratan_guard import GuardMiddleware

app = FastAPI()

# Initialize guard
guard = GuardMiddleware(enabled=True)

# Add rate limiting middleware
rate_limit_middleware = guard.create_rate_limit_middleware()
app.middleware("http")(rate_limit_middleware)

# Use guard in endpoints
@app.post("/ingest")
async def ingest(request: Request, data: IngestRequest):
    # Check request
    check_result = await guard.check_request(
        request,
        content=data.content,
        endpoint="/ingest"
    )
    
    if not check_result["allowed"]:
        raise HTTPException(status_code=403, detail="Request blocked")
    
    # Scrub PII if detected
    if check_result["pii_detected"]:
        data.content = guard.scrub_pii(data.content)
    
    # Process request...
```

## Audit Log Format

Audit logs are written to `audit.log` in JSON format:

```json
{
  "timestamp": "2024-01-01T12:00:00.000000",
  "event_type": "document_ingest",
  "user_id": "user456",
  "resource_id": "doc123",
  "action": "ingest",
  "result": "success",
  "metadata": {}
}
```

## Testing

Run tests with pytest:

```bash
cd packages/sheratan-guard
pytest tests/ -v
```

## Integration with Gateway

The sheratan-gateway automatically integrates guard features:

1. **Rate Limiting**: Applied to all endpoints via middleware
2. **PII Detection**: Automatic scrubbing in /ingest and /answer endpoints
3. **Policy Enforcement**: Content validation on all incoming requests
4. **Audit Logging**: All actions logged for compliance

## Integration with Orchestrator

The sheratan-orchestrator integrates guard features:

1. **PII Scrubbing**: Content cleaned before chunking
2. **Policy Checks**: Validation during document processing
3. **Audit Logging**: Document processing events logged

## Production Deployment

For production deployments:

1. Create `/etc/sheratan/guard/` directory
2. Copy example configs from `config-examples/` and customize
3. Set appropriate rate limits based on your infrastructure
4. Monitor `audit.log` for security events
5. Consider using Redis for distributed rate limiting (future enhancement)

## Security Considerations

- Rate limits are enforced per IP address
- PII detection uses regex patterns (may have false positives/negatives)
- Audit logs may contain sensitive information - secure accordingly
- Blocklists should be regularly updated
- For production, consider adding IP whitelisting/blacklisting
- Monitor audit logs for suspicious patterns
