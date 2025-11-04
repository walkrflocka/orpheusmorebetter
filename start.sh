#!/bin/sh
set -e

cd /app

echo "🔄 Starting OrpheusMoreBetter..."

# Optional: auto-update to latest commit
if [ -d .git ]; then
    echo "📦 Checking for updates..."
    git fetch --quiet origin || true
    git reset --hard origin/$(git rev-parse --abbrev-ref HEAD) || true
fi

# Record current version info
if [ -d .git ]; then
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
else
    GIT_COMMIT="unknown"
    GIT_BRANCH="unknown"
fi

echo "🔹 Git branch: ${GIT_BRANCH}"
echo "🔹 Git commit: ${GIT_COMMIT}"

echo "${GIT_BRANCH}" > /app/branch.txt
echo "${GIT_COMMIT}" > /app/version.txt

# Start the app
exec python -m orpheusmorebetter "$@"
