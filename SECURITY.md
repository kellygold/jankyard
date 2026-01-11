# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously at Jankyard.ai. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Email security concerns to the maintainers (see GitHub profile)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment:** Within 48 hours
- **Initial Assessment:** Within 1 week
- **Resolution Timeline:** Depends on severity, typically 2-4 weeks

### Scope

The following are in scope:
- Authentication/authorization bypasses
- Data exposure vulnerabilities
- Code injection (beyond the intentional prompt injection challenges)
- Server-side vulnerabilities

The following are **out of scope**:
- Prompt injection attacks on challenges (that's the point!)
- Rate limiting bypasses (annoying but not critical)
- UI/UX issues

### Recognition

We appreciate responsible disclosure and will credit researchers who report valid vulnerabilities (unless you prefer to remain anonymous).

## Security Best Practices for Contributors

1. Never commit secrets or API keys
2. Use `.env` for local configuration (it's gitignored)
3. Validate all user input
4. Use parameterized queries for database operations
5. Keep dependencies updated

Thank you for helping keep Jankyard secure!
