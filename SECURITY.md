# Security Policy

Security reports are taken seriously.

Minimal GitHub Stats runs inside GitHub Actions, uses GitHub API data, and generates an SVG that may be embedded in public profile README files.

## Supported versions

Security fixes are applied to the latest version available on the `main` branch.

| Version | Supported |
|---|---|
| Latest `main` branch | Yes |
| Older copies or forks | No |

Users of repositories created from this template should periodically review upstream changes and apply relevant security fixes.

## Reporting a vulnerability

Do not open a public issue when the report contains:

- GitHub tokens
- Repository secrets
- Private account information
- A method for executing unintended commands
- A workflow-permission vulnerability
- An SVG injection vulnerability
- Another issue that could place users at risk

Use GitHub's private vulnerability-reporting feature from the repository's **Security** tab when available.

Include:

- A clear description of the vulnerability
- The affected file or component
- Steps to reproduce it
- The possible impact
- A suggested fix, when known
- Any relevant logs with secrets removed

Please do not include active tokens, credentials, or private personal information.

## Expected response

A report will be reviewed as soon as reasonably possible.

After review, the maintainer may:

1. Confirm the report.
2. Request additional information.
3. Prepare and test a fix.
4. Publish the fix.
5. Credit the reporter, when requested and appropriate.

Public disclosure should wait until a fix is available.

## Security considerations

### GitHub tokens

The included workflow uses GitHub's temporary `GITHUB_TOKEN`.

Users should not add a personal access token unless they fully understand why it is required.

Never place a token directly inside:

- `config.json`
- `README.md`
- Python files
- Workflow files
- Generated SVG files
- Issues or pull requests

### Workflow permissions

The workflow requires:

```yaml
permissions:
  contents: write
