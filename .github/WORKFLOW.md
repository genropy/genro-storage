# Git Flow Workflow - genro-storage

## Overview

genro-storage uses **Git Flow** with protected branches to ensure code quality and stable releases.

## Branch Structure

```
main (protected)
  ↑
  └── PR required
       ↑
    develop (protected)
      ↑
      └── PR required
           ↑
        feature/*
        bugfix/*
```

### Branch Purposes

| Branch | Purpose | Protected | Merges From | Merges To |
|--------|---------|-----------|-------------|-----------|
| `main` | Production releases | ✅ Yes | `develop` (via release), `hotfix/*` | - |
| `develop` | Integration, next release | ✅ Yes | `feature/*`, `bugfix/*` | `main` (via release) |
| `feature/*` | New features | ❌ No | - | `develop` |
| `bugfix/*` | Bug fixes | ❌ No | - | `develop` |
| `hotfix/*` | Critical production fixes | ❌ No | `main` | `main` + `develop` |
| `release/*` | Release preparation | ❌ No | `develop` | `main` + `develop` |

## Protection Rules

Both `main` and `develop` are protected with:
- ✅ Require pull request before merging
- ✅ Require 1 approving review
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ❌ No force pushes
- ❌ No deletions
- ✅ Linear history not required (allows merge commits)

## Common Workflows

### 1. Working on a Feature

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/add-webdav-backend

# Make changes, commit
git add .
git commit -m "feat: add WebDAV backend support"

# Push and create PR to develop
git push origin feature/add-webdav-backend
gh pr create --base develop --head feature/add-webdav-backend
```

### 2. Fixing a Bug

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create bugfix branch
git checkout -b bugfix/fix-s3-timeout

# Make changes, commit
git add .
git commit -m "fix: increase S3 connection timeout"

# Push and create PR to develop
git push origin bugfix/fix-s3-timeout
gh pr create --base develop --head bugfix/fix-s3-timeout
```

### 3. Creating a Release

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/0.5.0

# Update version and changelog
vim pyproject.toml  # Update version
vim CHANGELOG.md    # Add release notes

# Commit release prep
git add .
git commit -m "chore: prepare release 0.5.0"

# Push and create PR to main
git push origin release/0.5.0
gh pr create --base main --head release/0.5.0 \
  --title "Release v0.5.0" \
  --body "Release version 0.5.0 with new features..."

# After PR approval and merge to main:
git checkout main
git pull origin main
git tag -a v0.5.0 -m "Release version 0.5.0"
git push origin v0.5.0

# Merge back to develop
gh pr create --base develop --head main \
  --title "Merge release 0.5.0 back to develop"

# Delete release branch
git branch -d release/0.5.0
git push origin --delete release/0.5.0
```

### 4. Hotfix for Production

```bash
# Branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# Fix issue
git add .
git commit -m "fix: patch critical security vulnerability"

# Push and create PR to main
git push origin hotfix/critical-security-fix
gh pr create --base main --head hotfix/critical-security-fix \
  --title "HOTFIX: Critical security patch"

# After merge to main, also merge to develop
gh pr create --base develop --head hotfix/critical-security-fix \
  --title "Merge hotfix to develop"

# Tag hotfix version
git checkout main
git pull origin main
git tag -a v0.4.2 -m "Hotfix: security patch"
git push origin v0.4.2
```

## Pull Request Guidelines

### PR to `develop`

- Base: `develop`
- Source: `feature/*` or `bugfix/*`
- Requirements:
  - All tests pass
  - Code coverage maintained
  - Documentation updated
  - 1 approving review

### PR to `main`

- Base: `main`
- Source: `release/*` or `hotfix/*`
- Requirements:
  - All tests pass
  - Version updated in `pyproject.toml`
  - CHANGELOG.md updated
  - Release notes prepared
  - 1 approving review

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Code style (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks
- `perf:` - Performance improvements

Examples:
```
feat: add WebDAV backend support
fix: resolve S3 timeout issue in large file uploads
docs: update contributing guidelines
chore: prepare release 0.5.0
```

## Bypassing Protection (Admins Only)

Admins can push directly to protected branches, but **should not**:
- Use this only for emergency hotfixes
- Document the reason in commit message
- Create a follow-up PR for review

## Tools

### GitHub CLI

```bash
# Create PR
gh pr create --base develop --head feature/my-feature

# List PRs
gh pr list

# Review PR
gh pr review 22 --approve
gh pr review 22 --comment -b "Looks good!"
gh pr review 22 --request-changes -b "Please fix..."

# Merge PR
gh pr merge 22
```

### Check Protection Status

```bash
# View branch protection
gh api repos/genropy/genro-storage/branches/main/protection

# View branch protection for develop
gh api repos/genropy/genro-storage/branches/develop/protection
```

## Troubleshooting

### "Protected branch update failed"

This means you tried to push directly to `main` or `develop`. Create a PR instead.

### "Pull request reviews required"

You need at least 1 approving review before merging. Request review from maintainers.

### Merge conflicts

```bash
# Update your feature branch with latest develop
git checkout feature/my-feature
git fetch origin
git merge origin/develop
# Resolve conflicts
git add .
git commit -m "merge: resolve conflicts with develop"
git push origin feature/my-feature
```

## Resources

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Full contribution guide
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [GitHub Protected Branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)

---

**Questions?** Open an issue or ask in pull requests.
