# Release Process for Lexicon AV Integration

This document describes how to create and publish new releases.

---

## Prerequisites

### Option 1: Manual Releases (GitHub CLI)

Install GitHub CLI:
```bash
# macOS with Homebrew
brew install gh

# Authenticate with GitHub
gh auth login
```

### Option 2: Automated Releases (GitHub Actions)

**No installation needed!** GitHub Actions runs automatically when you push a version tag.

---

## Release Checklist

Before creating a release, ensure:

- [ ] All code changes are committed
- [ ] Version bumped in `manifest.json`
- [ ] `CHANGELOG.md` updated with changes
- [ ] Release notes created (optional but recommended)
- [ ] Code tested on real hardware
- [ ] All GitHub Actions pass (if set up)

---

## Method 1: Automated Release via GitHub Actions (Recommended)

### How It Works

1. Push your changes to `main` branch
2. Create and push a version tag
3. GitHub Actions automatically:
   - Validates version matches manifest.json
   - Extracts release notes
   - Creates release archive
   - Publishes GitHub release
   - Attaches zip file

### Steps

**1. Update version in manifest.json**
```bash
# Edit custom_components/lexicon_av/manifest.json
# Change "version": "1.7.1" to "version": "1.7.2"
```

**2. Update CHANGELOG.md**
```bash
# Add entry at the top of CHANGELOG.md
## [1.7.2] - 2026-01-25

### Fixed
- Issue description here
```

**3. (Optional) Create release notes**
```bash
# Create RELEASE_NOTES_v1.7.2.md with user-friendly notes
```

**4. Commit and push changes**
```bash
git add .
git commit -m "1.7.2"
git push origin main
```

**5. Create and push tag**
```bash
# Create version tag
git tag v1.7.2

# Push tag to trigger GitHub Actions
git push origin v1.7.2
```

**6. Monitor GitHub Actions**
```bash
# View workflow run
gh run list

# Or visit: https://github.com/YOUR_USERNAME/lexicon-av-ha/actions
```

**Done!** GitHub Actions will create the release automatically.

---

## Method 2: Manual Release via Script

Use the provided script for more control.

### Steps

**1. Prepare as above (update version, changelog, etc.)**

**2. Run release script**
```bash
# From repository root
./scripts/create_release.sh v1.7.2

# Or let it detect version from manifest.json
./scripts/create_release.sh
```

**3. Verify release**
```bash
# View on GitHub
gh release view v1.7.2

# Or visit: https://github.com/YOUR_USERNAME/lexicon-av-ha/releases
```

---

## Method 3: Fully Manual (GitHub Web UI)

### Steps

**1. Prepare release as above**

**2. Create and push tag**
```bash
git tag v1.7.2
git push origin v1.7.2
```

**3. Create release archive**
```bash
cd custom_components
zip -r ../lexicon-av-v1.7.2.zip lexicon_av/ -x "*.pyc" -x "__pycache__/*"
cd ..
```

**4. Create release on GitHub**
1. Go to: https://github.com/YOUR_USERNAME/lexicon-av-ha/releases
2. Click "Draft a new release"
3. Choose tag: v1.7.2
4. Title: "Lexicon AV Integration v1.7.2"
5. Paste release notes
6. Attach: lexicon-av-v1.7.2.zip
7. Click "Publish release"

---

## Release Notes Template

Create `RELEASE_NOTES_v1.7.2.md` with this structure:

```markdown
# Release Notes: Lexicon AV Integration v1.7.2

**Release Date:** YYYY-MM-DD
**Type:** Bugfix / Feature / Major Release

## What's New

- Feature 1
- Feature 2

## What's Fixed

- Bug fix 1
- Bug fix 2

## Breaking Changes

None / List any breaking changes

## Migration Guide

Steps to upgrade from previous version

## Testing

How to verify the release works
```

---

## Version Numbering

Follow Semantic Versioning (SemVer):

- **Major (X.0.0)**: Breaking changes
- **Minor (1.X.0)**: New features, backwards compatible
- **Patch (1.7.X)**: Bug fixes, backwards compatible

Examples:
- `1.7.2` → `1.7.3`: Bug fix
- `1.7.2` → `1.8.0`: New features
- `1.7.2` → `2.0.0`: Breaking changes

---

## Post-Release Checklist

After creating a release:

- [ ] Verify release appears on GitHub
- [ ] Download and test zip file
- [ ] Update HACS (if listed)
- [ ] Announce in Home Assistant community
- [ ] Close related GitHub issues
- [ ] Update documentation if needed

---

## Troubleshooting

### "Version mismatch" error

**Problem:** Tag version doesn't match manifest.json

**Solution:**
```bash
# Check manifest version
grep "version" custom_components/lexicon_av/manifest.json

# Update manifest.json to match tag
# Then delete and recreate tag
git tag -d v1.7.2
git push origin :refs/tags/v1.7.2
git tag v1.7.2
git push origin v1.7.2
```

### "Release already exists"

**Problem:** Tag already has a release

**Solution:**
```bash
# Delete existing release
gh release delete v1.7.2

# Recreate release
./scripts/create_release.sh v1.7.2
```

### GitHub Actions not triggering

**Problem:** Workflow doesn't run on tag push

**Solution:**
1. Check `.github/workflows/release.yml` exists
2. Verify tag format matches (v*.*.*)
3. Check repository settings → Actions → Enabled
4. Ensure workflow has `contents: write` permission

---

## Automation Setup

### First-Time Setup

**1. Install GitHub CLI (for manual releases)**
```bash
brew install gh
gh auth login
```

**2. Configure GitHub Actions (for automated releases)**

No setup needed! Just ensure:
- `.github/workflows/release.yml` exists in your repo
- Repository Settings → Actions → Allow all actions

**3. Test automation**
```bash
# Create a test release
git tag v1.7.2-test
git push origin v1.7.2-test

# Watch workflow
gh run watch

# Delete test release
gh release delete v1.7.2-test
git tag -d v1.7.2-test
git push origin :refs/tags/v1.7.2-test
```

---

## Tips & Best Practices

1. **Always test before releasing** - Run your integration on real hardware
2. **Write clear release notes** - Users need to understand what changed
3. **Use semantic versioning** - Makes upgrade decisions easier
4. **Keep CHANGELOG updated** - Historical record of all changes
5. **Tag after everything is ready** - Tags trigger automation, so prepare first
6. **Use draft releases for testing** - Add `draft: true` in workflow
7. **Announce breaking changes** - Give users advance warning

---

## Example: Complete Release Workflow

```bash
# 1. Create feature branch
git checkout -b feature/timing-fixes

# 2. Make code changes
# ... edit files ...

# 3. Test thoroughly
# ... test on hardware ...

# 4. Update documentation
vim custom_components/lexicon_av/manifest.json  # version: 1.7.2
vim CHANGELOG.md                                 # Add entry
vim RELEASE_NOTES_v1.7.2.md                     # Create notes

# 5. Commit changes
git add .
git commit -m "Fix timing issues in boot sequence

- Increased boot timeout from 8s to 10s
- Removed verification loop from power_on()
- Added comprehensive stability check

Fixes #42"

# 6. Merge to main
git checkout main
git merge feature/timing-fixes
git push origin main

# 7. Create and push tag (triggers automation!)
git tag v1.7.2
git push origin v1.7.2

# 8. Wait for GitHub Actions
gh run watch

# 9. Verify release
gh release view v1.7.2

# 10. Announce
# Post in Home Assistant community forum
```

---

## Getting Help

- **GitHub Actions logs**: Check workflow runs for errors
- **Script issues**: Run with `bash -x scripts/create_release.sh`
- **GitHub CLI help**: `gh release --help`

---

**Happy Releasing!** 🚀
