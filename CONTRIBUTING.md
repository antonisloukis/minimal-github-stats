# Contributing to Minimal GitHub Stats

Thank you for considering a contribution.

Minimal GitHub Stats aims to remain lightweight, beginner-friendly, easy to configure, and independent of external statistics-card services.

## Ways to contribute

Useful contributions include:

- Fixing bugs
- Improving documentation
- Adding accessibility improvements
- Improving error messages
- Adding configuration options
- Creating additional themes
- Improving the SVG layout
- Reducing unnecessary API requests
- Adding tests
- Improving support for different GitHub profiles

Small, focused pull requests are preferred.

## Before starting

Before opening a pull request:

1. Search existing issues and pull requests.
2. Confirm that the change is not already being developed.
3. For large features, open an issue first and describe the proposal.
4. Keep each pull request focused on one improvement.

## Repository structure

```text
minimal-github-stats/
├── .github/
│   └── workflows/
│       └── update-stats.yml
├── assets/
│   └── github-stats.svg
├── scripts/
│   └── generate_stats.py
├── config.json
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

Important files:

- `scripts/generate_stats.py` contains the generator.
- `config.json` contains user-editable settings.
- `.github/workflows/update-stats.yml` runs the automation.
- `assets/github-stats.svg` is generated automatically.

Do not manually edit:

```text
assets/github-stats.svg
```

Any manual changes will be overwritten the next time the workflow runs.

## Development setup

### 1. Fork the repository

Create a fork under your GitHub account.

### 2. Clone your fork

```bash
git clone https://github.com/YOUR_USERNAME/minimal-github-stats.git
cd minimal-github-stats
```

### 3. Create a branch

Use a short, descriptive branch name:

```bash
git switch -c fix/language-percentage
```

Examples:

```text
feat/new-theme-option
fix/streak-calculation
docs/clarify-setup
refactor/graphql-client
```

### 4. Configure local authentication

Local execution requires a GitHub token.

Linux or macOS:

```bash
export GITHUB_TOKEN="your-token"
export GITHUB_USERNAME="your-username"
```

PowerShell:

```powershell
$env:GITHUB_TOKEN="your-token"
$env:GITHUB_USERNAME="your-username"
```

Never commit a token to the repository.

### 5. Run the generator

```bash
python scripts/generate_stats.py
```

The generated file will appear at:

```text
assets/github-stats.svg
```

## Testing changes

Before submitting a pull request, run:

```bash
python -m py_compile scripts/generate_stats.py
```

Then run the complete generator:

```bash
python scripts/generate_stats.py
```

Check that:

- The script exits successfully.
- The SVG is generated.
- The SVG opens correctly.
- Text is not clipped.
- Icons remain aligned.
- Multiple languages render correctly.
- Empty or limited language data does not break the card.
- Invalid configuration values produce clear errors.
- No token or private information appears in committed files.

For visual changes, include a screenshot in the pull request.

## Code guidelines

Please:

- Match the existing code style.
- Use clear variable and function names.
- Add type hints where practical.
- Keep functions focused.
- Handle failures with useful error messages.
- Escape user-controlled text before placing it in SVG.
- Prefer Python’s standard library.
- Avoid adding dependencies without discussing them first.
- Preserve beginner-friendly configuration.

## Configuration changes

When adding a new configuration option:

1. Add a safe default to `DEFAULT_CONFIG`.
2. Validate the new value.
3. Document it in `README.md`.
4. Include it in the fingerprint when it affects the SVG.
5. Confirm that older configuration files still work.

## Workflow changes

GitHub Actions permissions should remain minimal.

The workflow currently requires:

```yaml
permissions:
  contents: write
```

Do not add broader permissions unless the feature clearly requires them.

Workflow changes should:

- Avoid recursive workflow runs.
- Avoid unnecessary commits.
- Use the built-in `GITHUB_TOKEN`.
- Never expose secrets in logs.
- Remain compatible with repositories created from the template.

## Commit messages

Use clear commit messages.

Recommended prefixes:

```text
feat: add a new capability
fix: correct broken behavior
docs: improve documentation
refactor: reorganize code without changing behavior
test: add or update tests
chore: maintain project files or automation
```

Examples:

```text
fix: correct current streak calculation
docs: clarify profile README setup
feat: add compact card layout option
```

## Pull request checklist

Before opening a pull request, confirm:

- [ ] The change is focused.
- [ ] The Python file compiles.
- [ ] The generator runs successfully.
- [ ] The generated SVG renders correctly.
- [ ] Documentation is updated when necessary.
- [ ] No secrets or tokens are included.
- [ ] Visual changes include a screenshot.
- [ ] The pull request explains what changed and why.

## Pull request description

A useful pull request description should include:

- The problem being solved
- The proposed solution
- How the change was tested
- Any configuration changes
- Screenshots for visual modifications
- Related issue numbers

## Reporting bugs

When reporting a bug, include:

- What you expected
- What happened instead
- The relevant workflow error
- Your configuration, with secrets removed
- Steps to reproduce the problem
- Browser or operating system details when relevant

Never publish tokens or private account information.

## License

By contributing, you agree that your contribution may be distributed under the repository’s [MIT License](LICENSE).
