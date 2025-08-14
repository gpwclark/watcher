default:
    just check

# Install dependencies
install:
    uv sync

# Apply those lints which can be fixed automatically.
fix:
    uv run ruff check --fix .

# Run linting
lint:
    uv run ruff check .

# Format code
format:
    uv run ruff format .

# Check linting and formatting
check:
    uv run ruff check .
    uv run ruff format --check .

# test
test:
    uv run --extra test pytest
