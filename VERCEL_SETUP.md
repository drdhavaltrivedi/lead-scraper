# 🚀 Vercel Deployment - Optimized Configuration

This app has been restructured specifically for Vercel's serverless architecture.

## Key Changes for Vercel

### 1. **Synchronous Scraping**
- Removed session-based approach (stateless functions)
- Results returned directly in API response
- No background threads or polling needed

### 2. **Timeout Optimization**
- Limited to 20 results for simple search (fits within 60-second timeout)
- Limited to 15 results for ICP mode
- Faster scraping with reduced scrolls and timeouts

### 3. **Simplified Architecture**
- Removed `scraping_sessions` dictionary (stateless)
- Removed threading and background processing
- Direct async/await pattern

## Deployment Steps

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy**:
   ```bash
   vercel
   ```
   Or connect your GitHub repo in Vercel dashboard for automatic deployments.

## Configuration

The `vercel.json` file is configured with:
- Python 3.12 runtime
- 60-second function timeout (Pro plan) or 10 seconds (Hobby plan)
- Proper routing for API endpoints

## Limitations

⚠️ **Important Vercel Limitations:**

1. **Timeout Limits:**
   - Hobby plan: 10 seconds max
   - Pro plan: 60 seconds max
   - This limits the number of results you can scrape

2. **Stateless Functions:**
   - No persistent memory between requests
   - Each request is independent
   - No session storage (that's why we removed it)

3. **Playwright Dependencies:**
   - Vercel may have issues with Playwright browser dependencies
   - Consider using Railway for full Playwright support

## File Structure

- `app.py` - Vercel-optimized Flask app (synchronous, stateless)
- `app_railway.py` - Original Railway version (with sessions, background threads)
- `vercel.json` - Vercel configuration
- `index.html` - Frontend (updated for synchronous responses)

## Switching Back to Railway

If you need the full-featured version:
1. Rename files: `mv app.py app_vercel.py && mv app_railway.py app.py`
2. Deploy to Railway (which supports long-running processes)

## Testing

After deployment, test the endpoints:
- `GET /api/test` - Verify API is working
- `POST /api/scrape` - Test scraping (limited to 20 results)
- `POST /api/scrape-icp` - Test ICP mode (limited to 15 results)

## Troubleshooting

**404 Errors:**
- Check `vercel.json` routing configuration
- Ensure `handler = app` is exported in `app.py`

**Timeout Errors:**
- Reduce `max_results` further
- Check your Vercel plan (Hobby = 10s, Pro = 60s)

**Playwright Errors:**
- Vercel may not support Playwright fully
- Consider Railway for better Playwright support

