#!/usr/bin/env bash
# Pack the agent repo for import (ClawHub, Convex, or manual install).
# Output: dist/gstd-a2a-import.tar.gz — extract and run: pip install -r requirements.txt && pip install -e . && python3 main.py

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
ARCHIVE_NAME="gstd-a2a-import"
TAR_PATH="${DIST_DIR}/${ARCHIVE_NAME}.tar.gz"
TMP_DIR="${DIST_DIR}/.pack-$$"

mkdir -p "$DIST_DIR"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR/$ARCHIVE_NAME"

# Files and dirs needed for import (manifest, entrypoint, SDK, deps, starter-kit for config)
cp "$REPO_ROOT/manifest.json" "$TMP_DIR/$ARCHIVE_NAME/"
cp "$REPO_ROOT/main.py" "$TMP_DIR/$ARCHIVE_NAME/"
cp "$REPO_ROOT/requirements.txt" "$TMP_DIR/$ARCHIVE_NAME/"
cp "$REPO_ROOT/setup.py" "$TMP_DIR/$ARCHIVE_NAME/"
cp "$REPO_ROOT/pyproject.toml" "$TMP_DIR/$ARCHIVE_NAME/" 2>/dev/null || true
cp "$REPO_ROOT/README.md" "$TMP_DIR/$ARCHIVE_NAME/" 2>/dev/null || true
cp "$REPO_ROOT/SKILL.md" "$TMP_DIR/$ARCHIVE_NAME/" 2>/dev/null || true
cp "$REPO_ROOT/IMPORT.md" "$TMP_DIR/$ARCHIVE_NAME/" 2>/dev/null || true
cp -r "$REPO_ROOT/python-sdk" "$TMP_DIR/$ARCHIVE_NAME/"
find "$TMP_DIR/$ARCHIVE_NAME/python-sdk" -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
find "$TMP_DIR/$ARCHIVE_NAME/python-sdk" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
cp -r "$REPO_ROOT/starter-kit" "$TMP_DIR/$ARCHIVE_NAME/"

# Create tarball
(cd "$TMP_DIR" && tar czf "$TAR_PATH" "$ARCHIVE_NAME")

# ZIP with top-level folder (generic)
ZIP_PATH="${DIST_DIR}/${ARCHIVE_NAME}.zip"
python3 -c "
import zipfile, os
z = zipfile.ZipFile('${ZIP_PATH}', 'w', zipfile.ZIP_DEFLATED)
root = '${TMP_DIR}/${ARCHIVE_NAME}'
for d, _, files in os.walk(root):
    for f in files:
        path = os.path.join(d, f)
        arc = os.path.relpath(path, '${TMP_DIR}')
        z.write(path, arc)
z.close()
"

# ZIP for ClawHub: files at root (SKILL.md, manifest.json at root — https://clawhub.ai/upload)
CLWHUB_ZIP="${DIST_DIR}/gstd-a2a-clawhub.zip"
python3 -c "
import zipfile, os
z = zipfile.ZipFile('${CLWHUB_ZIP}', 'w', zipfile.ZIP_DEFLATED)
root = '${TMP_DIR}/${ARCHIVE_NAME}'
for d, _, files in os.walk(root):
    for f in files:
        path = os.path.join(d, f)
        arc = os.path.relpath(path, root)
        z.write(path, arc)
z.close()
"

rm -rf "$TMP_DIR"

echo "Created: $TAR_PATH"
echo "Created: $ZIP_PATH"
echo "Created: $CLWHUB_ZIP  <- use for https://clawhub.ai/upload"
echo "To use: unzip ${ARCHIVE_NAME}.zip && cd $ARCHIVE_NAME && pip install -r requirements.txt && pip install -e . && python3 main.py"
