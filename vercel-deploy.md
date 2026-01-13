# Deploying Lead Scraper to Vercel

## Important Note
⚠️ **Vercel has limitations for this application:**
- Vercel Serverless Functions have a 10-second timeout (Hobby plan) or 60 seconds (Pro)
- Playwright requires a full server environment and may not work well in serverless
- This app needs long-running processes for scraping

## Recommended Alternatives

### 1. **Railway** (Recommended)
- Free tier available
- Supports long-running processes
- Easy deployment from GitHub
- Steps:
  1. Go to https://railway.app
  2. Sign up with GitHub
  3. New Project → Deploy from GitHub
  4. Select your repository
  5. Add environment variables if needed
  6. Deploy!

### 2. **Render**
- Free tier available
- Supports Flask apps
- Steps:
  1. Go to https://render.com
  2. Sign up with GitHub
  3. New → Web Service
  4. Connect your GitHub repo
  5. Build command: `pip install -r requirements.txt`
  6. Start command: `python app.py`
  7. Deploy!

### 3. **Fly.io**
- Free tier available
- Great for Python apps
- Steps:
  1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
  2. Run: `fly launch`
  3. Follow prompts

### 4. **Heroku** (Paid, but reliable)
- Classic platform for Flask apps
- Steps:
  1. Install Heroku CLI
  2. `heroku create your-app-name`
  3. `git push heroku main`

## If you still want to try Vercel:

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Follow prompts
4. Note: You may need to modify the app for serverless compatibility

