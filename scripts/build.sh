#!/bin/sh
# Build the deployable site into dist/ — only what the browser needs, nothing else from the repo
# (docs, reference material, .claude, serve.py stay private).
# Cloudflare Pages: build command `sh scripts/build.sh`, output directory `dist`.
set -e
rm -rf dist
mkdir -p dist
cp index.html dist/
cp -r vendor brand dist/
[ -d assets ] && cp -r assets dist/
[ -d layouts ] && cp -r layouts dist/
# Long-cache the pinned library and brand files; always revalidate the app page itself.
cat > dist/_headers <<'EOF'
/vendor/*
  Cache-Control: public, max-age=31536000, immutable
/brand/*
  Cache-Control: public, max-age=86400
/index.html
  Cache-Control: no-cache
/
  Cache-Control: no-cache
EOF
echo "Built dist/:"
ls -R dist | head -40
