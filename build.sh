#!/bin/bash
set -e

echo "🔧 Installing system dependencies for Playwright..."

# Install system dependencies required by Chromium
apt-get update
apt-get install -y \
  libglib2.0-0 \
  libnss3 \
  libnspr4 \
  libdbus-1-3 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libcups2 \
  libdrm2 \
  libxcb1 \
  libxkbcommon0 \
  libatspi2.0-0 \
  libx11-6 \
  libxcomposite1 \
  libxdamage1 \
  libxext6 \
  libxfixes3 \
  libxrandr2 \
  libgbm1 \
  libpango-1.0-0 \
  libcairo2 \
  libasound2

echo "✅ System dependencies installed"

# Install Python dependencies
python -m venv /opt/venv
source /opt/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers and dependencies
echo "🌐 Installing Playwright..."
playwright install chromium
playwright install-deps chromium

echo "✅ Build complete!"

