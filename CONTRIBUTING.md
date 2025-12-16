# Contributing to Industrial Data System

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Quality Standards](#code-quality-standards)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- pip

### Setup Development Environment

1. Clone the repository:
```bash
git clone https://github.com/Mijog-ai/IndustrialDataSystem.git
cd IndustrialDataSystem
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install-dev
# or
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Development Workflow

### 1. Create a Branch

Create a feature branch from `develop`:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications

### 2. Make Changes

- Write clean, readable code
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write docstrings for public functions and classes
- Add tests for new functionality

### 3. Format and Check Code

Before committing, ensure your code meets quality standards:

```bash
# Format code automatically
make format

# Run all quality checks
make check

# Run type checking
make typecheck

# Run linters
make lint

# Run security checks
make security
```

Or run everything at once:
```bash
make quality
```

### 4. Run Tests

```bash
make test
```

Ensure all tests pass and coverage remains high (>80%).

### 5. Commit Changes

Pre-commit hooks will automatically run before each commit. If they fail, fix the issues and commit again.

```bash
git add .
git commit -m "feat: add new feature description"
```

See [Commit Messages](#commit-messages) for formatting guidelines.

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub targeting the `develop` branch.

## Code Quality Standards

All code must meet these standards before being merged:

### Required Checks

- ✅ **Black formatting**: Code must be formatted with Black
- ✅ **Import sorting**: Imports must be sorted with isort
- ✅ **Flake8 linting**: No Flake8 errors
- ✅ **Pylint score**: Minimum score of 8.0/10
- ✅ **Type hints**: All functions must have type hints
- ✅ **MyPy**: No type checking errors
- ✅ **Security**: No Bandit security issues
- ✅ **Tests**: All tests must pass
- ✅ **Coverage**: Minimum 80% code coverage

### Type Hints Example

```python
from typing import List, Dict, Optional, Union
from pathlib import Path

def process_files(
    file_paths: List[Path],
    output_dir: Path,
    config: Optional[Dict[str, Union[str, int]]] = None
) -> bool:
    """Process files and save to output directory.

    Args:
        file_paths: List of file paths to process
        output_dir: Directory to save processed files
        config: Optional configuration dictionary

    Returns:
        True if processing succeeded, False otherwise

    Raises:
        ValueError: If file_paths is empty
        FileNotFoundError: If any file doesn't exist
    """
    if not file_paths:
        raise ValueError("file_paths cannot be empty")

    # Implementation here
    return True
```

### Error Handling Standards

Follow the patterns documented in [CODE_QUALITY.md](CODE_QUALITY.md#error-handling):

1. **Catch specific exceptions** - Don't use bare `except:`
2. **Provide context** - Include meaningful error messages
3. **Use custom exceptions** - Define domain-specific exceptions
4. **Log appropriately** - Log errors with sufficient detail
5. **Clean up resources** - Use context managers

Example:
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DataProcessingError(Exception):
    """Custom exception for data processing failures."""
    pass

def process_data(data: Optional[str]) -> str:
    """Process data with proper error handling.

    Args:
        data: Input data to process

    Returns:
        Processed data

    Raises:
        ValueError: If data is None or empty
        DataProcessingError: If processing fails
    """
    if not data:
        raise ValueError("Data cannot be empty")

    try:
        result = expensive_operation(data)
        logger.info("Data processed successfully")
        return result
    except SpecificError as e:
        logger.error(f"Processing failed: {e}")
        raise DataProcessingError(f"Failed to process data: {e}") from e
```

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Examples

```
feat(auth): add user authentication system

Implement JWT-based authentication with login and logout endpoints.
Includes password hashing and token refresh functionality.

Closes #123
```

```
fix(database): resolve connection pool exhaustion

Fix issue where database connections were not being properly released
back to the pool, causing exhaustion under high load.

Fixes #456
```

```
docs: update installation instructions in README

Add details about Python version requirements and virtual environment setup.
```

## Pull Request Process

### Before Submitting

1. ✅ All tests pass locally
2. ✅ Code is formatted and linted
3. ✅ Type checking passes
4. ✅ Documentation is updated
5. ✅ Commit messages follow conventions
6. ✅ Branch is up to date with develop

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- List of specific changes
- Another change
- etc.

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added that prove fix/feature works
- [ ] Dependent changes merged
```

### Review Process

1. Automated checks must pass (GitHub Actions)
2. At least one approved review required
3. No unresolved conversations
4. Branch must be up to date with base branch

### After Approval

Once approved and checks pass:
1. Squash and merge to `develop`
2. Delete feature branch
3. Update local repository

## Code Review Guidelines

### For Authors

- Keep PRs small and focused
- Respond to feedback promptly
- Update PR based on review comments
- Test thoroughly before requesting review

### For Reviewers

- Review within 2 business days
- Be constructive and specific
- Suggest improvements, don't demand
- Approve when requirements are met

## Getting Help

- Check [CODE_QUALITY.md](CODE_QUALITY.md) for coding standards
- Review existing code for examples
- Ask questions in PR comments
- Open an issue for discussion

## Additional Resources

- [Code Quality Guidelines](CODE_QUALITY.md)
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Type Hints (PEP 484)](https://www.python.org/dev/peps/pep-0484/)

Thank you for contributing! 🎉
