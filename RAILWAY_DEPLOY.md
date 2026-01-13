# 🚂 Deploying Lead Scraper to Railway

Railway is the **recommended platform** for this application because it:
- ✅ Supports long-running processes (perfect for scraping)
- ✅ Has a free tier with $5 credit monthly
- ✅ Easy GitHub integration
- ✅ Supports Playwright and browser automation
- ✅ Automatic deployments on git push

## Quick Deploy Steps

### Option 1: Deploy via Railway Dashboard (Easiest)

1. **Sign up for Railway**
   - Go to https://railway.app
   - Click "Start a New Project"
   - Sign up with your GitHub account

2. **Deploy from GitHub**
   - Click "Deploy from GitHub repo"
   - Select your repository: `drdhavaltrivedi/lead-scraper`
   - Railway will automatically detect it's a Python project

3. **Configure Build Settings**
   - Railway will use the `railway.json` and `nixpacks.toml` files
   - Build command: `pip install -r requirements.txt && playwright install chromium`
   - Start command: `python app.py`

4. **Set Environment Variables** (if needed)
   - Usually not required for this app
   - But you can add custom variables in Railway dashboard

5. **Deploy!**
   - Railway will automatically build and deploy
   - You'll get a URL like: `https://your-app-name.up.railway.app`

6. **Access Your App**
   - Click on the deployed service
   - Go to "Settings" → "Generate Domain"
   - Or use the default Railway domain

### Option 2: Deploy via Railway CLI

1. **Install Railway CLI**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login**
   ```bash
   railway login
   ```

3. **Initialize Project**
   ```bash
   cd /home/brilworks/lead-scraper
   railway init
   ```

4. **Deploy**
   ```bash
   railway up
   ```

## Important Notes

### Playwright Installation
Railway will automatically install Chromium during the build process using the configuration files we've added.

### Port Configuration
The app is configured to use the `PORT` environment variable that Railway provides automatically.

### Free Tier Limits
- Railway free tier gives $5 credit per month
- After that, pay-as-you-go pricing
- Monitor usage in Railway dashboard

### Troubleshooting

**If Playwright fails to install:**
- Check Railway build logs
- Ensure `playwright install chromium` runs during build

**If app doesn't start:**
- Check logs: `railway logs`
- Verify port is set correctly (Railway sets PORT automatically)

**If scraping doesn't work:**
- Railway supports long-running processes, so scraping should work
- Check browser logs in Railway dashboard

## Post-Deployment

1. **Test the deployment**
   - Visit your Railway URL
   - Try scraping a few leads
   - Check that everything works

2. **Monitor Usage**
   - Check Railway dashboard for resource usage
   - Monitor logs for any errors

3. **Custom Domain (Optional)**
   - Go to Settings → Domains
   - Add your custom domain
   - Railway will provide DNS instructions

## Continuous Deployment

Railway automatically deploys when you push to GitHub:
- Push to `main` branch → Auto-deploy
- Check Railway dashboard for deployment status

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

