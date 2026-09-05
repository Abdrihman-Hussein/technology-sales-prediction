# Contributing to Kaamil Technology Sales

Thank you for your interest in contributing! This document outlines how to get started.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/kaamil-technology-sales.git
   cd kaamil-technology-sales
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy environment config**
   ```bash
   cp .env.example .env
   ```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Code Style

- Use type hints where practical
- Keep functions focused — one responsibility each
- Add docstrings to public functions and classes
- Follow existing naming conventions (snake_case for functions/variables)

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `test:` — adding or updating tests
- `chore:` — maintenance tasks
- `ci:` — CI/CD changes

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes with tests
3. Ensure all tests pass: `python -m pytest tests/ -v`
4. Open a PR with a clear description of the change
5. Wait for CI checks to pass and request review

## Reporting Issues

Open an issue on GitHub with:
- A clear title and description
- Steps to reproduce (if applicable)
- Expected vs actual behavior
