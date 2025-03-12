# UL Transit Data Collector

This is a FastAPI application that collects and processes transit data from Uppsala Lokaltrafik (UL), providing real-time vehicle positions and an event-based API for subscribers to receive updates.

## Features

- Collects vehicle position data from UL's GTFS Realtime API at a specified interval
- Stores vehicle position data in a PostgreSQL database
- Provides REST API endpoints for retrieving vehicle positions
- Implements an event-based API using WebSockets for real-time notifications
- Integrated startup - all components start simultaneously
- Supports manual triggering of data collection cycles
- Docker containerization for easy deployment
- CI/CD automation with GitHub Actions

## Requirements

- Python 3.11+
- PostgreSQL database
- Environment variables (see `.env.example`)
- Docker (optional, for containerized deployment)
- API key for Uppsala Länstrafik API

## Setup

### Local Setup

1. Clone this repository
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Set up environment variables (copy `.env.example` to `.env` and modify as needed)
5. Create a PostgreSQL database and update the `.env` file with the connection details

### Docker Setup

1. Clone this repository
2. Create a `.env` file based on `.env.example`
3. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

This will start both the application and a PostgreSQL database. The application will be available at http://localhost:8001.

## Running the Application

### Local Startup

The application features an integrated startup process that ensures all components start simultaneously:

```bash
python run.py
```

This will:
1. Start the FastAPI application with all API endpoints
2. Start the background data collection scheduler
3. Trigger an initial data collection cycle
4. Set up event broadcasting

### Docker Startup

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

### Using the Pre-built Docker Image

You can also use our pre-built Docker image from GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/jorand-hogia/poc-ul-data-gatherer:latest

# Run the container with your .env file
docker run -d --name ul-data-collector -p 8001:8001 --env-file .env ghcr.io/jorand-hogia/poc-ul-data-gatherer:latest
```

### Testing the API

A test client script is included to verify that the API is working correctly:

```bash
python test_client.py
```

The test client:
1. Checks the health endpoint to verify the API is running
2. Lists available event types
3. Retrieves the latest vehicle positions
4. Connects to the WebSocket API
5. Subscribes to various event types
6. Triggers a data collection cycle
7. Listens for events and logs them

If successful, you should see output confirming each step and showing the events received.

## API Documentation

When the application is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## API Endpoints

### Health Check

- `GET /health` - Returns the health status of the application

### Vehicle Positions

- `GET /api/v1/vehicle-positions/latest` - Returns the latest vehicle positions
- `GET /api/v1/vehicle-positions/history/{vehicle_id}` - Returns the position history for a specific vehicle

### Event-Based API

The application provides an event-based API that allows clients to subscribe to events and receive real-time updates.

#### Event Types

- `vehicle_position_update` - Triggered when a vehicle position is updated
- `vehicle_route_change` - Triggered when a vehicle changes its route
- `data_collection_start` - Triggered to start a new data collection cycle
- `data_collection_complete` - Triggered when a data collection cycle is complete

#### REST Endpoints

- `GET /api/v1/events/event-types` - Returns the list of available event types
- `POST /api/v1/events/trigger-event/{event_type}` - Triggers an event of the specified type
- `GET /api/v1/events/history/{event_type}` - Returns the history of events of the specified type

#### WebSocket Endpoint

- `WebSocket /api/v1/events/ws/{client_id}` - Connects to the event stream
  - After connecting, send a subscription message: `{"action": "subscribe", "event_types": ["event_type1", "event_type2"]}`
  - To unsubscribe: `{"action": "unsubscribe", "event_types": ["event_type1"]}`

## Integration with Other Systems

Other systems can integrate with this application in several ways:

1. **REST API**: Make HTTP requests to the REST API endpoints
2. **WebSocket API**: Connect to the WebSocket endpoint and subscribe to events
3. **Manual Trigger**: Trigger data collection or other events using the `trigger-event` endpoint

## Monitoring

The application provides a health check endpoint at `/health` that returns the current state of the application, including:
- API readiness status
- Database connection status
- Scheduler status
- Current timestamp

## Manual Control

You can manually trigger data collection outside the regular schedule:

```bash
curl -X POST http://localhost:8001/api/v1/events/trigger-event/data_collection_start
```

## Docker CI/CD

This project uses GitHub Actions to automatically:
1. Build the Docker image
2. Run tests
3. Push the Docker image to GitHub Container Registry
4. Create a new release when a tag is pushed

The Docker image is built and pushed on every push to the `master` branch and when a new tag is created.

## Error Handling

The application includes robust error handling for:
- Connection issues with the GTFS Realtime API
- Database connection problems
- Invalid WebSocket subscriptions

## Development and Testing

### Testing

The project uses pytest for testing. To run the tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Generate coverage report
coverage report
```

### Code Quality

We use pylint for code quality checks:

```bash
# Run pylint on the app directory
pylint app
```

Common issues found by pylint in this codebase include:
- Logging f-string interpolation (use % formatting instead)
- Broad exception catching
- Imports outside toplevel
- Singleton comparisons (use `is` instead of `==` for boolean constants)

### CI/CD Pipeline

The project uses GitHub Actions for CI/CD:
1. Run tests and linting
2. Build and push Docker image (on main branch or tags)
3. Create GitHub release (on version tags)

## Manual Control

To manually trigger data collection outside the regular schedule:

```bash
curl -X POST http://localhost:8001/api/v1/events/trigger \
  -H "Content-Type: application/json" \
  -d '{"event_type": "data_collection_start", "data": {}}'
```

## Health Check

Check if the application is running properly:

```bash
curl http://localhost:8001/health
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request 