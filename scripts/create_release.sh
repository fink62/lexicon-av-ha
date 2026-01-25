#!/bin/bash
# Create GitHub Release for Lexicon AV Integration
#
# Usage: ./scripts/create_release.sh v1.7.2

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get version from argument or manifest.json
VERSION="$1"
if [ -z "$VERSION" ]; then
    VERSION=$(grep '"version"' custom_components/lexicon_av/manifest.json | sed 's/.*: "\(.*\)".*/\1/')
    echo -e "${YELLOW}No version specified, using version from manifest.json: ${VERSION}${NC}"
fi

# Ensure version starts with 'v'
if [[ ! "$VERSION" =~ ^v ]]; then
    VERSION="v${VERSION}"
fi

echo -e "${GREEN}Creating release for version: ${VERSION}${NC}"

# Check if version exists in CHANGELOG
if ! grep -q "\[${VERSION#v}\]" CHANGELOG.md; then
    echo -e "${RED}ERROR: Version ${VERSION} not found in CHANGELOG.md${NC}"
    echo "Please update CHANGELOG.md before creating a release"
    exit 1
fi

# Check if release notes exist
RELEASE_NOTES="RELEASE_NOTES_${VERSION}.md"
if [ ! -f "$RELEASE_NOTES" ]; then
    echo -e "${YELLOW}WARNING: ${RELEASE_NOTES} not found${NC}"
    echo "Extracting from CHANGELOG.md..."

    # Extract release notes from CHANGELOG
    sed -n "/## \[${VERSION#v}\]/,/^## \[/p" CHANGELOG.md | sed '$d' > /tmp/release_notes.md
    RELEASE_NOTES="/tmp/release_notes.md"
fi

# Verify clean working directory
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}WARNING: Working directory is not clean${NC}"
    git status --short
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create and push tag
echo -e "${GREEN}Creating and pushing tag...${NC}"
git tag -a "$VERSION" -m "Release $VERSION"
git push origin "$VERSION"

# Create GitHub release
echo -e "${GREEN}Creating GitHub release...${NC}"
gh release create "$VERSION" \
    --title "Lexicon AV Integration $VERSION" \
    --notes-file "$RELEASE_NOTES" \
    --draft=false \
    --prerelease=false

# Create release archive
echo -e "${GREEN}Creating release archive...${NC}"
ARCHIVE_NAME="lexicon-av-${VERSION}.zip"
cd custom_components
zip -r "../${ARCHIVE_NAME}" lexicon_av/ -x "*.pyc" -x "__pycache__/*" -x ".DS_Store"
cd ..

# Upload archive to release
echo -e "${GREEN}Uploading release archive...${NC}"
gh release upload "$VERSION" "$ARCHIVE_NAME"

# Cleanup
rm -f "$ARCHIVE_NAME"
if [ "$RELEASE_NOTES" = "/tmp/release_notes.md" ]; then
    rm -f /tmp/release_notes.md
fi

echo -e "${GREEN}✅ Release ${VERSION} created successfully!${NC}"
echo ""
echo "View release: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/releases/tag/${VERSION}"
