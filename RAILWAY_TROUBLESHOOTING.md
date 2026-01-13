# Railway Deployment Troubleshooting

## Current Status
🌐 **Deployment URL**: https://web-production-8914.up.railway.app

## Common Issues & Solutions

### Issue 1: 404 Error - Application Not Found

**Possible Causes:**
- App is still building/deploying
- App crashed during startup
- Port configuration issue
- Build failed

**Solutions:**

1. **Check Railway Dashboard:**
   - Go to your Railway project dashboard
   - Check the "Deployments" tab
   - Look for build logs and errors
   - Check if the deployment is "Active" or "Failed"

2. **Check Build Logs:**
   - In Railway dashboard, click on your service
   - Go to "Deployments" → Click on latest deployment
   - Check for errors in build logs
   - Common issues:
     - Playwright installation failing
     - Missing dependencies
     - Python version mismatch

3. **Check Runtime Logs:**
   - In Railway dashboard, go to "Logs" tab
   - Look for startup errors
   - Check if the app is listening on the correct port

4. **Verify Port Configuration:**
   - Railway automatically sets `PORT` environment variable
   - Our app should use: `port = int(os.environ.get('PORT', 5000))`
   - Make sure this is in `app.py`

### Issue 2: Playwright Installation Failing

**Solution:**
Add this to your Railway build settings or `nixpacks.toml`:
```toml
[phases.install]
cmds = [
  "pip install -r requirements.txt",
  "playwright install chromium",
  "playwright install-deps chromium"
]
```

### Issue 3: App Crashes on Startup

**Check:**
1. Railway logs for Python errors
2. Missing environment variables
3. Import errors
4. Port binding issues

**Fix:**
- Ensure all imports are correct
- Check that `requirements.txt` has all dependencies
- Verify `app.py` uses `PORT` from environment

### Issue 4: Build Timeout

**Solution:**
- Playwright installation can take time
- Railway free tier has build time limits
- Consider upgrading or optimizing build

## Quick Fixes

### 1. Restart the Service
In Railway dashboard:
- Go to your service
- Click "Settings" → "Restart"

### 2. Redeploy
- Go to "Deployments"
- Click "Redeploy" on latest deployment

### 3. Check Environment Variables
- Go to "Variables" tab
- Ensure `PORT` is set (Railway sets this automatically)
- Add any custom variables if needed

### 4. Verify Build Configuration
Check that Railway is using:
- **Build Command**: `pip install -r requirements.txt && playwright install chromium`
- **Start Command**: `python app.py`

## Testing the Deployment

Once fixed, test with:
```bash
# Check if app is running
curl https://web-production-8914.up.railway.app/

# Test API endpoint
curl -X POST https://web-production-8914.up.railway.app/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"location":"New York","work_type":"restaurant","max_results":2}'
```

## Getting Help

1. **Railway Logs**: Check dashboard logs for detailed errors
2. **Railway Discord**: https://discord.gg/railway
3. **Railway Docs**: https://docs.railway.app

## Next Steps

1. ✅ Check Railway dashboard for deployment status
2. ✅ Review build logs for any errors
3. ✅ Check runtime logs for startup issues
4. ✅ Verify the app is listening on the correct port
5. ✅ Test the deployment once it's running

