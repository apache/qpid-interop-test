# Broker Setup for QIT

QIT requires an AMQP 1.0 broker with specific configuration for auto-creating queues and using anycast (queue) routing.

## Option 1: Local Artemis Instance (Recommended - Tested ✓)

This matches the original Jenkins setup and has been verified to work with QIT 2.0.

### Prerequisites

Download and install Apache ActiveMQ Artemis:
- Download from: https://activemq.apache.org/components/artemis/download/
- Extract and add `bin/artemis` to your PATH

### Setup

```bash
# Run setup script (creates broker in ./artemis-local)
./scripts/setup-local-broker.sh

# Start broker
./artemis-local/bin/artemis run
```

The broker will be configured with:
- **No persistence** (faster for testing)
- **Auto-create queues** for `qit.#` and `test.#` patterns  
- **ANYCAST routing** (queue semantics, not topic)
- **Anonymous access** enabled
- **AMQP on port 5672**

### Verify

```bash
# In another terminal, run a test
source .venv/bin/activate
qit test amqp-types --type boolean --type uint
```

## Option 2: Docker with Apache Artemis (Tested ✓)

Uses the official Apache Artemis Docker image with configuration override.

**Status**: Tested and working with `apache/artemis:latest-alpine` image.

### Usage

```bash
# Start broker
docker compose -f docker/compose.yaml up -d

# Check logs
docker compose -f docker/compose.yaml logs -f

# Stop broker
docker compose -f docker/compose.yaml down
```

### How It Works

The broker configuration is overridden using the `etc-override` mechanism:
- Custom `broker.xml` in `docker/etc-override/` directory
- Mounted to `/var/lib/artemis-instance/etc-override/` in container
- Automatically copied to `/var/lib/artemis-instance/etc/` after instance creation

**Important**: Use the official `apache/artemis` image, not `artemiscloud/activemq-artemis-broker`. The artemiscloud image does not support the etc-override mechanism.

### Previous Attempts

~~May need to either:~~
1. Create a custom Dockerfile that bakes in the configuration
2. Use an init container to modify broker.xml before startup
3. Use the volume mount approach (needs more investigation)

## Option 3: Qpid Dispatch Router

An alternative lightweight broker that auto-creates queues by default.

```bash
# Install dispatch router
sudo dnf install qpid-dispatch-router

# Start with default config
qdrouterd
```

## Required Broker Configuration

Regardless of broker choice, the following is required:

### For Artemis

```xml
<address-settings>
   <address-setting match="qit.#">
      <auto-create-addresses>true</auto-create-addresses>
      <auto-create-queues>true</auto-create-queues>
      <default-address-routing-type>ANYCAST</default-address-routing-type>
   </address-setting>
   
   <address-setting match="test.#">
      <auto-create-addresses>true</auto-create-addresses>
      <auto-create-queues>true</auto-create-queues>
      <default-address-routing-type>ANYCAST</default-address-routing-type>
   </address-setting>
</address-settings>

<!-- Optional: Disable persistence for faster testing -->
<persistence-enabled>false</persistence-enabled>
```

### Why This Configuration?

1. **auto-create-queues**: QIT uses dynamic queue names (e.g., `qit.test.uint.python-proton.cpp-proton`) that can't be pre-configured
2. **ANYCAST routing**: Ensures messages are stored in queues (point-to-point) rather than topics (publish-subscribe)
3. **No persistence**: Faster startup and testing, messages don't need to survive broker restarts

## Troubleshooting

### Messages not received

Check broker logs for:
```
AMQ221003: Deploying ANYCAST queue <queue-name> on address <address-name>
```

If you don't see this, the auto-create configuration isn't working.

### Permission denied

Ensure anonymous access is enabled:
```bash
artemis create --allow-anonymous ...
```

Or use credentials in the broker URL:
```python
broker_url = "amqp://admin:admin@localhost:5672"
```

### Port 5672 already in use

Kill any existing broker:
```bash
./artemis-local/bin/artemis-service stop
# or
pkill -9 -f artemis
```
