# Security Inspection Rules

## Overview
These rules focus on identifying security vulnerabilities and ensuring secure coding practices.

## OWASP Top 10 Checks

### 1. Injection Vulnerabilities
- **SQL Injection**: Use parameterized queries, avoid string concatenation
- **Command Injection**: Validate and sanitize shell commands
- **Code Injection**: Avoid eval() and similar dynamic code execution
- **LDAP Injection**: Sanitize LDAP queries
- **XML Injection**: Use safe XML parsers

### 2. Broken Authentication
- Password storage: Use strong hashing (bcrypt, argon2, scrypt)
- Session management: Secure session tokens, proper timeout
- Multi-factor authentication: Implement where appropriate
- No hardcoded credentials in source code

### 3. Sensitive Data Exposure
- Encryption at rest: Sensitive data must be encrypted
- Encryption in transit: Use TLS 1.2+ for all communications
- No sensitive data in logs or error messages
- Proper key management

### 4. XML External Entities (XXE)
- Disable external entity processing in XML parsers
- Use safe XML parsing libraries
- Validate XML inputs

### 5. Broken Access Control
- Implement proper authorization checks
- Deny by default access control
- No insecure direct object references
- Validate user permissions on every request

### 6. Security Misconfiguration
- Remove default credentials
- Disable unnecessary features and services
- Keep frameworks and libraries up to date
- Proper error handling (no stack traces to users)

### 7. Cross-Site Scripting (XSS)
- Sanitize all user inputs
- Use context-aware output encoding
- Implement Content Security Policy (CSP)
- Validate and encode data in all contexts

### 8. Insecure Deserialization
- Avoid deserializing untrusted data
- Implement integrity checks
- Use safe serialization formats (JSON over pickle/marshal)

### 9. Using Components with Known Vulnerabilities
- Keep all dependencies updated
- Monitor security advisories
- Use dependency scanning tools
- Remove unused dependencies

### 10. Insufficient Logging & Monitoring
- Log all authentication and authorization events
- Log all input validation failures
- Implement alerting for suspicious activities
- Protect log files from tampering

## Cryptography

### 1. Encryption Standards
- Use AES-256 for symmetric encryption
- Use RSA-2048+ or ECC for asymmetric encryption
- Avoid weak algorithms (DES, RC4, MD5, SHA1)

### 2. Random Number Generation
- Use cryptographically secure RNG
- Avoid predictable seeds
- Proper IV generation for encryption

### 3. Certificate Validation
- Validate SSL/TLS certificates
- Check certificate expiration
- Verify certificate chains

## Authentication & Authorization

### 1. Password Requirements
- Minimum length: 8 characters
- Complexity requirements
- Password history
- Account lockout after failed attempts

### 2. Session Management
- Generate strong session IDs
- Implement session timeout
- Invalidate sessions on logout
- Secure cookie flags (HttpOnly, Secure, SameSite)

### 3. API Security
- Implement rate limiting
- Use API keys or OAuth tokens
- Validate all API inputs
- Implement proper CORS policies

## Data Protection

### 1. Personal Identifiable Information (PII)
- Minimize PII collection
- Encrypt PII at rest and in transit
- Implement data retention policies
- Provide data deletion mechanisms

### 2. Payment Information
- PCI-DSS compliance for card data
- Never store CVV/CVC codes
- Use payment processors for sensitive operations

### 3. Data Validation
- Whitelist validation over blacklist
- Validate data type, length, format, and range
- Sanitize file uploads
- Validate file types and sizes

## Network Security

### 1. Communication Security
- Use HTTPS for all web traffic
- Implement HSTS headers
- Disable insecure protocols (SSLv3, TLS 1.0, TLS 1.1)

### 2. API Endpoints
- No sensitive data in URLs
- Implement authentication on all endpoints
- Use POST for state-changing operations
- Validate Content-Type headers

## File Operations

### 1. File Upload
- Validate file types by content, not extension
- Limit file sizes
- Store uploads outside web root
- Scan files for malware

### 2. File Access
- Prevent directory traversal attacks
- Validate file paths
- Use allowlists for file access
- Implement proper file permissions

## Code Security

### 1. Input Validation
- Validate all external inputs
- Use type checking
- Implement length and range checks
- Reject invalid input, don't sanitize

### 2. Output Encoding
- Context-aware encoding
- Encode data for HTML, JavaScript, URL, CSS contexts
- Use framework-provided encoding functions

### 3. Secure Coding Practices
- Principle of least privilege
- Fail securely
- Don't trust client-side validation
- Implement defense in depth

## Database Security

### 1. Query Security
- Use parameterized queries or ORMs
- Avoid dynamic SQL construction
- Implement query timeouts
- Limit database privileges

### 2. Connection Security
- Use encrypted connections
- Implement connection pooling
- Use read-only connections where appropriate

## Container & Infrastructure Security

### 1. Container Security
- Use minimal base images
- Don't run as root
- Scan images for vulnerabilities
- Keep images updated

### 2. Secrets Management
- Use secret management tools (Vault, etc.)
- No secrets in environment variables
- Rotate secrets regularly

## Compliance

### 1. Regulatory Requirements
- GDPR compliance for EU data
- HIPAA for healthcare data
- SOC 2 requirements
- Industry-specific regulations

## Severity Classification

- **Critical**: Remote code execution, authentication bypass, data breach
- **High**: Privilege escalation, XSS, CSRF, sensitive data exposure
- **Medium**: Information disclosure, weak cryptography, security misconfiguration
- **Low**: Security best practice violations, minor vulnerabilities

## Scoring Impact

Security issues should significantly impact the overall quality score:
- Critical issue: -20 points
- High issue: -10 points
- Medium issue: -5 points
- Low issue: -2 points
