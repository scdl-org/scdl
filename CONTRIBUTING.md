# Contributing to SCDL

Thank you for your interest in contributing to SCDL! This document provides guidelines for contributing to the project.

## 🚀 Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/your-username/scdl.git`
3. **Install** development dependencies: `uv sync`
4. **Make** your changes
5. **Test** your changes: `uv run pytest`
6. **Submit** a pull request

## 📋 Development Setup

### Prerequisites
- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- ffmpeg (for audio processing)

### Installation
```bash
# Clone the repository
git clone https://github.com/scdl-org/scdl.git
cd scdl

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .[dev]
```

## 🧪 Testing

Run the test suite:
```bash
uv run pytest
```

For tests that require authentication:
```bash
export AUTH_TOKEN=your_soundcloud_token
uv run pytest
```

## 🎯 Code Quality

We maintain high code quality standards:

### Linting
```bash
uv run ruff check
uv run ruff format
```

### Type Checking
```bash
uv run mypy
```

## 📝 Pull Request Guidelines

1. **Create an issue** first to discuss major changes
2. **Keep changes focused** - one feature/fix per PR
3. **Write clear commit messages** using [Conventional Commits](https://www.conventionalcommits.org/)
4. **Add tests** for new functionality
5. **Update documentation** if needed
6. **Ensure all CI checks pass**

### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat: add support for playlist batch download`
- `fix: resolve authentication token expiry issue`
- `docs: update installation instructions`

## 🐛 Bug Reports

When reporting bugs, please include:
- **SCDL version** (`scdl --version`)
- **Python version** (`python --version`)
- **Operating system**
- **Complete command** that caused the issue
- **Full error output**
- **Expected vs actual behavior**

## 💡 Feature Requests

Before requesting features:
1. **Check existing issues** to avoid duplicates
2. **Consider if it can be achieved** with `--yt-dlp-args`
3. **Provide clear use cases** and examples

## 🔒 Security

To report security vulnerabilities:
- **DO NOT** create public issues
- **Email** the maintainers privately
- **Provide** detailed information about the vulnerability

## 📖 Documentation

Help improve documentation by:
- **Fixing typos** and grammar errors
- **Adding examples** for complex use cases
- **Improving clarity** of explanations
- **Updating outdated information**

## 🎉 Recognition

Contributors are recognized in:
- Git commit history
- Release notes
- Project documentation

Thank you for helping make SCDL better! 🎵
