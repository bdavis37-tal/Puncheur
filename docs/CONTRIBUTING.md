# Contributing to Puncheur

## Setup

```bash
# Clone the repo
git clone https://github.com/bdavis37-tal/Puncheur.git
cd Puncheur

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Code Style

- Python 3.11+
- Type hints everywhere
- Docstrings on all public functions and classes
- No print statements — use Rich console or logging
- Line length: 100 characters (configured in pyproject.toml)

## Testing

- All analytics modules should have unit tests
- Use synthetic data (see `tests/conftest.py`) for deterministic assertions
- Run the full suite: `pytest`
- Run with coverage: `pytest --cov=puncheur`

## Pull Requests

1. Fork the repo
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a PR with a clear description

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for how the codebase is organized.

## Reporting Issues

When reporting bugs, include:
- Python version
- OS
- Minimal reproduction steps
- The FIT file (if applicable, anonymized GPS data is fine)
