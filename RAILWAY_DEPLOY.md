# 🚀 Quick Deploy to Railway (Recommended)

Railway is the easiest way to deploy your FastAPI application with background scheduler.

## Why Railway?

✅ **Perfect for this app** - Supports long-running background processes  
✅ **Free to start** - $5 free credit per month  
✅ **Zero configuration** - Works out of the box  
✅ **Auto-deploys** - Push to GitHub → Auto-deploy  
✅ **Built-in monitoring** - View logs and metrics

---

## Deployment Steps (2 minutes)

### Method 1: Web Interface (Easiest)

1. **Sign Up**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Auto-Deploy**
   - Railway automatically:
     - Detects Python
     - Installs dependencies from requirements.txt
     - Starts your app
   - Done! ✅

4. **Get Your URL**
   - Go to "Settings" tab
   - Click "Generate Domain"
   - Your app is live at: `https://your-app.up.railway.app`

5. **Test**
   ```bash
   curl https://your-app.up.railway.app/health
   ```

---

### Method 2: Railway CLI (Optional)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up

# Generate domain
railway domain

# View logs
railway logs
```

---

## Configuration

### Environment Variables (Optional)

If you want to use environment variables instead of hardcoded config:

1. In Railway dashboard → "Variables" tab
2. Add variables:
   ```
   LEADPIER_USERNAME=hello@shaktallc.com
   LEADPIER_PASSWORD=Shakta123!
   PORT=8000
   SCHEDULE_INTERVAL_MINUTES=10
   ```

---

## Monitoring

### View Logs

1. Go to Railway dashboard
2. Click on your service
3. Click "Logs" tab
4. See real-time logs

### Check Scheduler

- Visit: `https://your-app.up.railway.app/status`
- Shows scheduler status and job statistics

### Health Check

- Visit: `https://your-app.up.railway.app/health`
- Returns: `{"status": "healthy", "scheduler_running": true}`

---

## Pricing

- **Hobby Plan**: $5 free credit per month
- **Usage**: ~$2-3/month for small apps
- Your app should stay within free credit

---

## Troubleshooting

### App not starting?

- Check logs in Railway dashboard
- Ensure requirements.txt is present
- Verify Python version (3.12 recommended)

### Scheduler not running?

- Check `/status` endpoint
- View logs for scheduler messages
- Ensure no crashes on startup

### Need help?

- Railway Discord: https://discord.gg/railway
- Documentation: https://docs.railway.app

---

## Next Steps

1. Deploy to Railway (2 minutes)
2. Generate domain
3. Test endpoints:
   - `/health` - Health check
   - `/status` - Scheduler status
   - `/logs` - View logs
   - `/trigger` - Manual job trigger
   - `/docs` - API documentation

---

## 🎉 That's it!

Your LeadPier sync service is now running in the cloud with:

- ✅ Automatic data sync every 10 minutes
- ✅ 24/7 uptime
- ✅ Automatic restarts on failure
- ✅ Real-time monitoring
- ✅ Easy updates via GitHub push

**Total time: 2 minutes** ⚡
