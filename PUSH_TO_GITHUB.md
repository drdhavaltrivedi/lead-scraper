# 🚀 Pushing to GitHub - Step by Step Guide

## Option 1: Using GitHub CLI (Recommended)

If you have GitHub CLI installed:

```bash
# Create repository on GitHub
gh repo create lead-scraper --public --source=. --remote=origin --push

# Or if repository already exists:
gh repo create lead-scraper --public --source=. --remote=origin
git push -u origin main
```

## Option 2: Manual GitHub Setup

### Step 1: Create Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `lead-scraper`
3. Description: "Automated Business Data Extraction Tool - Web-based lead generation application"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### Step 2: Add Remote and Push

```bash
# Add GitHub remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/lead-scraper.git

# Rename branch to main if needed
git branch -M main

# Push to GitHub
git push -u origin main
```

### Step 3: If Using SSH

```bash
# Add SSH remote
git remote add origin git@github.com:YOUR_USERNAME/lead-scraper.git

# Push
git push -u origin main
```

## Option 3: Using GitHub Desktop

1. Open GitHub Desktop
2. File → Add Local Repository
3. Select the `/home/brilworks/lead-scraper` folder
4. Click "Publish repository"
5. Choose name and visibility
6. Click "Publish repository"

## Current Repository Status

✅ Git initialized
✅ All files committed
✅ Ready to push

## Next Steps After Pushing

1. Add topics/tags on GitHub: `web-scraping`, `lead-generation`, `python`, `flask`, `playwright`
2. Add a description: "Automated Business Data Extraction Tool"
3. Consider adding a license file (MIT, Apache 2.0, etc.)
4. Enable GitHub Pages if you want to host the frontend

