# Contributing to EffortlessHome

Thank you for your interest in contributing to EffortlessHome! We welcome contributions from the community and appreciate your help in making this integration better.

## Code of Conduct

Please be respectful and constructive in all interactions with other community members and maintainers.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Home Assistant development environment
- Git
- Understanding of Home Assistant custom components

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/EffortlessHome.git
   cd EffortlessHome
   ```

3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Set up Home Assistant development environment**:
   - Install Home Assistant in development mode: `pip install -e .`
   - Run Home Assistant with your local changes

## Development Guidelines

### Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for function parameters and return values
- Use meaningful variable and function names
- Keep functions focused and reasonably sized
- Add docstrings to classes and public functions

Example:
```python
def handle_motion_detection(entity_id: str, area: str) -> bool:
    """
    Handle motion detection for an entity in a specific area.
    
    Args:
        entity_id: The entity ID to process
        area: The area where motion was detected
        
    Returns:
        True if motion was successfully processed, False otherwise
    """
    # Implementation here
    pass
```

### Project Structure

- **Core integration logic**: `__init__.py`, `config_flow.py`, `const.py`
- **Platform implementations**: `sensor.py`, `binary_sensor.py`, `switch.py`, etc.
- **Feature modules**: `alarm_common.py`, `motion_notification.py`, `sleep_mode.py`, etc.
- **Blueprints**: `blueprints/` directory for automation blueprints
- **Translations**: `translations/` directory for i18n support

### Important Files

- `manifest.json`: Integration metadata and dependencies
- `strings.json`: User-facing strings for configuration
- `services.yaml`: Service definitions
- `const.py`: Constants and configuration defaults

## Making Changes

### Before You Start

1. **Check existing issues and PRs** to avoid duplicate work
2. **Discuss major changes** by opening an issue first
3. **Keep changes focused** - one feature or fix per PR

### Working on Features

1. **Create a feature branch** from `main`
2. **Implement your changes** following the code style guidelines
3. **Add tests** if applicable
4. **Update documentation** including docstrings and README if needed
5. **Update `strings.json`** if you add new user-facing strings
6. **Test thoroughly** with Home Assistant

### Working on Bug Fixes

1. **Create a branch** describing the bug: `fix/issue-description`
2. **Fix the issue** with minimal, focused changes
3. **Add a comment** referencing the original issue
4. **Test** to ensure the fix works and doesn't introduce regressions

## Testing

### Manual Testing

- Test your changes with a real Home Assistant instance
- Verify all related features still work correctly
- Test edge cases and error conditions

### Areas to Focus On

- Integration setup and configuration flow
- Entity creation and updates
- Service calls and automation triggers
- Blueprint functionality
- Error handling and logging

## Submitting Changes

### Creating a Pull Request

1. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to related issues (if applicable)
   - List of any breaking changes

3. **PR Title Format**:
   - `feat: Add new feature name`
   - `fix: Fix issue description`
   - `docs: Update documentation`
   - `refactor: Refactor component name`

### PR Description Template

```markdown
## Description
Brief description of the change

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #(issue number)

## Testing
Describe how you tested this change

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or breaking change noted)
- [ ] Tested with Home Assistant
```

## Areas of Focus

### High Priority Areas

- **Security**: Always be mindful of security implications
- **Performance**: Avoid unnecessary network calls or processing
- **Reliability**: Proper error handling and edge case coverage
- **User Experience**: Consider usability in configuration and automation

### Common Contribution Areas

- **Bug Fixes**: Always welcome
- **New Features**: Discuss in issues first
- **Documentation**: Help improve clarity and examples
- **Blueprints**: Add new automation blueprints for common scenarios
- **Translations**: Help translate the integration to new languages
- **Tests**: Improve test coverage and reliability

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**: What's the issue?
2. **Steps to Reproduce**: How can we reproduce it?
3. **Expected Behavior**: What should happen?
4. **Actual Behavior**: What actually happens?
5. **Environment**:
   - Home Assistant version
   - EffortlessHome version
   - Python version
   - Relevant hardware/devices
6. **Logs**: Include relevant error messages or debug logs
7. **Screenshots**: Visual representation if applicable

### Feature Requests

When requesting features, include:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Are there existing alternatives?
4. **Additional Context**: Any other relevant information

## Documentation

- Update docstrings when modifying functions
- Update README.md for user-facing changes
- Add comments for complex logic
- Update services.yaml if adding new services
- Update strings.json for new configuration options

## Commit Messages

Write clear, descriptive commit messages:

```
feat: Add motion sensor grouping for security

- Implement intelligent grouping of motion sensors
- Add configuration options for group behavior
- Include blueprint for motion-based automation

Closes #123
```

### Commit Message Guidelines

- Start with type: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Use present tense ("Add feature" not "Added feature")
- Keep the first line under 50 characters
- Reference issues and PRs when relevant

## Licensing

By contributing to EffortlessHome, you agree that your contributions will be licensed under the [Apache License Version 2.0](LICENSE).

## Questions?

- Check existing [GitHub Issues](https://github.com/EffortlessHome/EffortlessHome/issues)

## Recognition

Contributors will be recognized in:
- Release notes for significant contributions
- README.md acknowledgments section
- GitHub contributors page

Thank you for contributing to EffortlessHome! 🎉
