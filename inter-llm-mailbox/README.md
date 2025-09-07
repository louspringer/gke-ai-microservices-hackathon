# Inter-LLM Mailbox System

A distributed messaging infrastructure that enables asynchronous communication between Large Language Model instances using Redis as the underlying pub/sub and storage engine.

## Features

- **Asynchronous Messaging**: Send and receive messages between LLM instances
- **Real-time Communication**: Pub/sub messaging with immediate delivery
- **Persistent Storage**: Store-and-forward messaging for offline participants
- **Topic-based Communication**: Group messaging with hierarchical topics
- **Security & Permissions**: Role-based access control and audit logging
- **Multiple Content Types**: Support for text, JSON, binary, and code content
- **Resilient Design**: Circuit breakers, retry logic, and graceful degradation

## Architecture

The system consists of four primary layers:

1. **Client Layer**: LLM instances connect through standardized client libraries
2. **API Layer**: RESTful and WebSocket APIs for message operations
3. **Core Layer**: Message routing, subscription management, and permission enforcement
4. **Storage Layer**: Redis-based persistence and pub/sub infrastructure

## Project Structure

```
inter-llm-mailbox/
├── src/
│   ├── models/          # Core data models
│   ├── core/            # Core business logic components
│   ├── api/             # REST and WebSocket APIs
│   └── client/          # Client library for LLM integration
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Getting Started

### Prerequisites

- Python 3.9+
- Redis 6.0+

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start Redis server:
   ```bash
   redis-server
   ```

### Running Tests

```bash
pytest tests/
```

## Development Status

This project is currently under development. The following components have been implemented:

- ✅ Core data models (Message, Subscription, Permission)
- ✅ Basic validation and serialization
- ✅ Unit tests for data models
- 🚧 Redis connection management (in progress)
- 🚧 Core components (planned)
- 🚧 API layer (planned)
- 🚧 Client library (planned)

## Contributing

This project follows systematic development practices with comprehensive testing and documentation.

## License

[License information to be added]