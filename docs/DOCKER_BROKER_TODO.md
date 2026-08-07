# Docker Broker Configuration - TODO

## Current Status

Attempting to configure Artemis in Docker to support auto-queue creation for QIT.

## Challenge

The Artemis Docker image creates the broker instance on first start. We need to modify `broker.xml` AFTER it's created but BEFORE the broker starts accepting connections.

## Approaches Tried

1. **Volume mount override**: Didn't work (path incorrect)
2. **Custom entrypoint script**: Timing issue - broker.xml not yet created when script runs
3. **XML override file**: Need to find correct override mechanism

## Known Working Solution

**Local Artemis** with `setup-local-broker.sh`:
```bash
artemis create --allow-anonymous broker
sed -i 's/persistence/...' broker/etc/broker.xml  
sed -i '/<\/address-settings>/i ...' broker/etc/broker.xml
broker/bin/artemis run
```

## Recommended Next Steps

### Option A: Use docker-compose with init command
```yaml
services:
  artemis:
    image: quay.io/artemiscloud/activemq-artemis-broker:latest
    entrypoint: /bin/bash
    command: |
      -c "
      # Let base image create instance
      /opt/amq/bin/launch.sh &
      PID=\$!
      # Wait for broker.xml
      while [ ! -f /home/jboss/broker/etc/broker.xml ]; do sleep 1; done
      # Modify config
      sed -i '/<\/address-settings>/i <address-setting match=\"qit.#\">...</address-setting>' /home/jboss/broker/etc/broker.xml
      # Continue
      wait \$PID
      "
```

### Option B: Multi-stage Dockerfile
```dockerfile
# Stage 1: Create and configure instance
FROM artemis as builder
RUN artemis create /tmp/broker ...
RUN sed -i ... /tmp/broker/etc/broker.xml

# Stage 2: Copy configured instance
FROM artemis
COPY --from=builder /tmp/broker /home/jboss/broker
```

### Option C: Use Dispatch Router instead
Dispatch Router auto-creates queues by default, simpler configuration:
```yaml
services:
  dispatch:
    image: quay.io/interconnectedcloud/qdrouterd
    ports:
      - "5672:5672"
```

### Option D: Document Docker limitation, use local broker
Update documentation to recommend local Artemis for development, Docker for CI once we figure out the config.

## Recommendation

For now: **Use local Artemis** (working), revisit Docker later.

The local setup script (`scripts/setup-local-broker.sh`) works perfectly and matches the Jenkins environment. Getting Docker working is nice-to-have but not blocking for Phase 2.

## Files Created

- `docker/Dockerfile.artemis` - Custom image (WIP)
- `docker/configure-broker.sh` - Config script (timing issues)
- `docker/broker-config-override.xml` - Override attempt
- `docker/compose.yaml` - Updated to build custom image

These can be refined later once we find the right approach.
