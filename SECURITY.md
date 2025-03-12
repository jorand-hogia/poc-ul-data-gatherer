# Security Policy

## Supported Versions

This project is currently in development, and security updates will be applied to the latest version only.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

To report a security vulnerability, please email jorgen.andersson@hogia.se with details about the vulnerability.

We take security issues seriously and will respond to your report within 48 hours.

Please include the following information in your report:
- Type of issue
- Location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

We request that you do not publicly disclose the issue until we have had a chance to address it.

## Security Best Practices

This application implements the following security measures:
- Environment variables for sensitive configuration
- Database connection pooling with proper authentication
- Input validation for all API endpoints
- CORS restrictions for WebSocket connections
- Error handling that doesn't expose sensitive information

## Third-Party Dependencies

We regularly scan our dependencies for known vulnerabilities and update them as needed. 