# Code Quality Inspection Rules

## Overview
These rules define the code quality standards that should be enforced during code inspection.

## Code Structure

### 1. File Organization
- Files should be logically organized by feature or module
- Maximum file length: 500 lines (excluding comments)
- Related files should be grouped in appropriate directories

### 2. Function/Method Design
- Functions should have a single responsibility
- Maximum function length: 50 lines
- Maximum number of parameters: 5
- Avoid deep nesting (max 4 levels)

### 3. Class Design
- Classes should follow Single Responsibility Principle
- Prefer composition over inheritance
- Maximum class length: 300 lines

## Naming Conventions

### 1. Variables
- Use descriptive names that reflect purpose
- Avoid single-letter names except for loop counters
- Use camelCase for JavaScript/TypeScript, snake_case for Python
- Boolean variables should be prefixed with is/has/should

### 2. Functions/Methods
- Use verb-noun format (e.g., getUserData, calculateTotal)
- Names should describe what the function does
- Avoid abbreviations unless commonly understood

### 3. Classes
- Use PascalCase
- Names should be nouns or noun phrases
- Avoid generic names like Manager, Helper, Utility

## Code Quality

### 1. Comments and Documentation
- All public APIs must have documentation
- Complex logic should have explanatory comments
- Comments should explain "why", not "what"
- Avoid commented-out code

### 2. Error Handling
- All error cases should be handled explicitly
- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately

### 3. Code Duplication
- No duplicated code blocks (DRY principle)
- Extract common functionality into reusable functions
- Maximum acceptable duplication: 3 lines

### 4. Code Complexity
- Cyclomatic complexity should be less than 10
- Avoid deeply nested conditionals
- Break complex conditions into named variables

## Testing

### 1. Test Coverage
- Minimum test coverage: 80%
- All public APIs must have tests
- Critical business logic must have unit tests

### 2. Test Quality
- Tests should be independent and isolated
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

## Dependencies

### 1. Dependency Management
- All dependencies should be explicitly declared
- Avoid unused dependencies
- Keep dependencies up to date
- Pin dependency versions

### 2. Import Management
- Remove unused imports
- Group imports logically
- Avoid circular dependencies

## Performance

### 1. Algorithmic Efficiency
- Avoid O(n²) or worse algorithms where possible
- Use appropriate data structures
- Consider lazy loading for large datasets

### 2. Resource Management
- Close file handles and connections properly
- Avoid memory leaks
- Use connection pooling where appropriate

## Security Considerations

### 1. Input Validation
- Validate all user inputs
- Sanitize data before use
- Use parameterized queries for database operations

### 2. Sensitive Data
- No hardcoded credentials or secrets
- Use environment variables for configuration
- Avoid logging sensitive information

## Code Style

### 1. Formatting
- Consistent indentation (2 or 4 spaces)
- Maximum line length: 100-120 characters
- Consistent brace style
- Proper whitespace usage

### 2. Language-Specific Best Practices
- Follow language idioms and conventions
- Use modern language features appropriately
- Avoid deprecated APIs

## Version Control

### 1. Commit Quality
- Commits should be atomic and focused
- Meaningful commit messages
- No generated files in version control

## Scoring Guidelines

- **90-100**: Excellent - Follows all best practices
- **80-89**: Good - Minor improvements needed
- **70-79**: Fair - Several issues to address
- **60-69**: Poor - Significant refactoring needed
- **0-59**: Critical - Major quality issues

## Issue Severity Levels

- **Critical**: Security vulnerabilities, data loss risks, system crashes
- **High**: Major bugs, performance issues, architectural problems
- **Medium**: Code quality issues, maintainability concerns
- **Low**: Style issues, minor improvements, suggestions
