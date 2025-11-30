# Contributing to Telegram AI Image Generation Bot

Thank you for your interest in contributing to the Telegram AI Image Generation Bot! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Documentation](#documentation)
- [License](#license)

## Code of Conduct

This project adheres to a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive in all interactions
- Focus on constructive feedback and collaboration
- Accept responsibility for mistakes and learn from them
- Show empathy towards other contributors
- Help create a positive community environment

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- Python 3.11 or higher installed
- Git for version control
- A Telegram bot token (for testing)
- A Stability AI API key (for testing)
- Basic understanding of Python and Telegram bot development

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/telegram-image-generation-bot.git
   cd telegram-image-generation-bot
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/telegram-image-generation-bot.git
   ```

## Development Setup

### Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create environment configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. Run the bot for testing:
   ```bash
   cd code/
   python main.py
   ```

### Development Tools

- **Code Editor**: Use any Python-compatible editor (VS Code, PyCharm, etc.)
- **Linting**: The project uses built-in Python linting
- **Version Control**: Git with the provided .gitignore
- **Testing**: Manual testing with Telegram bot interactions

## How to Contribute

### Types of Contributions

- **Bug Fixes**: Identify and fix issues in the codebase
- **New Features**: Implement new image generation capabilities
- **Documentation**: Improve or add documentation
- **Code Quality**: Refactor code for better maintainability
- **Testing**: Add or improve test coverage

### Contribution Workflow

1. **Choose an Issue**: Look for open issues or create a new one
2. **Create a Branch**: Use descriptive branch names
   ```bash
   git checkout -b feature/add-new-style-preset
   git checkout -b bugfix/fix-timeout-handling
   git checkout -b docs/improve-api-documentation
   ```
3. **Make Changes**: Implement your contribution following the guidelines
4. **Test Thoroughly**: Ensure your changes work correctly
5. **Commit Changes**: Follow commit message guidelines
6. **Push and Create PR**: Push to your fork and create a pull request

## Code Standards

### Python Code Style

- Follow PEP 8 style guidelines
- Use 4 spaces for indentation
- Limit line length to 88 characters
- Use descriptive variable and function names
- Include comprehensive docstrings for all public functions

### Code Structure

- **Separation of Concerns**: Keep modules focused on specific responsibilities
- **Type Hints**: Use type annotations for function parameters and return values
- **Error Handling**: Implement proper exception handling with meaningful messages
- **Logging**: Use appropriate logging levels and structured messages

### File Organization

- `main.py`: Application entry point and orchestration
- `routes.py`: Telegram command handlers and conversation flows
- `models.py`: Data structures and configuration classes
- `helper.py`: Business logic and external API integrations
- Tests should be placed in a `tests/` directory when added

## Testing

### Manual Testing Requirements

Since this is a Telegram bot, testing requires:

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test API integrations with mock services
3. **End-to-End Tests**: Manual testing with actual Telegram bot

### Testing Checklist

Before submitting a pull request, ensure:

- [ ] Code runs without syntax errors
- [ ] Bot starts successfully with proper configuration
- [ ] All existing commands work as expected
- [ ] New features work as intended
- [ ] Error handling works correctly
- [ ] No breaking changes to existing functionality

### API Testing

When testing API integrations:

- Use test API keys when available
- Implement proper rate limiting
- Test error scenarios (invalid keys, network issues, API limits)
- Verify response parsing and error handling

## Commit Guidelines

### Commit Message Format

Use clear, descriptive commit messages following this format:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(imagine): add support for aspect ratio selection

fix(timeout): resolve conversation timeout handling bug

docs(readme): update installation instructions

refactor(routes): simplify command handler structure
```

### Commit Best Practices

- Keep commits focused on single changes
- Use present tense in commit messages
- Reference issue numbers when applicable
- Squash related commits before final merge

## Pull Request Process

### Creating a Pull Request

1. **Ensure Branch is Updated**: Rebase on the latest main branch
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run Final Tests**: Verify everything works correctly

3. **Create PR**: Use a descriptive title and detailed description
   - Reference related issues
   - Describe the changes made
   - Include screenshots for UI changes
   - List any breaking changes

### PR Template

Use this structure for pull request descriptions:

```
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how the changes were tested.

## Screenshots (if applicable)
Add screenshots to show visual changes.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests pass successfully
- [ ] Documentation updated
- [ ] No breaking changes
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: Maintainers review code for quality and correctness
3. **Feedback**: Address review comments and make necessary changes
4. **Approval**: PR is approved and merged
5. **Cleanup**: Delete the feature branch after merge

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Step-by-step instructions
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: Python version, OS, bot version
- **Logs**: Relevant error messages or log output
- **Screenshots**: Visual evidence of the issue

### Feature Requests

For new features, please provide:

- **Description**: Detailed description of the proposed feature
- **Use Case**: Why this feature would be useful
- **Implementation Ideas**: Suggestions for implementation
- **Alternatives**: Other solutions considered

### Issue Labels

Issues are categorized with labels:

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Documentation improvements
- `help wanted`: Good first issue for new contributors
- `question`: Questions or discussions

## Documentation

### Documentation Standards

- Use clear, concise language
- Include code examples where helpful
- Keep documentation up to date with code changes
- Use proper markdown formatting
- Include table of contents for longer documents

### Documentation Files

- `README.md`: Project overview and setup instructions
- `code/README.md`: Technical module documentation
- `CONTRIBUTING.md`: This contribution guide
- Inline code comments for complex logic

## License

By contributing to this project, you agree that your contributions will be licensed under the same MIT License that covers the project. See the [LICENSE](LICENSE) file for details.

---

Thank you for contributing to the Telegram AI Image Generation Bot! Your contributions help make this project better for everyone.
