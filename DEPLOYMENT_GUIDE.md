# Deployment Guide

## ⚠️ Vercel Compatibility Issue

**Your application is NOT compatible with Vercel** in its current form because:

1. **Background Scheduler** - APScheduler requires a continuously running process
2. **Persistent Storage** - source.json and logs won't persist in serverless
3. **Long-Running Jobs** - Vercel has 10-300s timeout limits

---

## ✅ Recommended: Railway Deployment (Best Option)

Railway is perfect for your FastAPI app with background scheduler.

### Step 1: Prepare Your Project

1. **Create .gitignore:**

```gitignore
__pycache__/
*.pyc
.env
.venv/
venv/
logs/
source.json
*.log
.DS_Store
```

2. **Create Procfile (optional, Railway auto-detects):**

```
web: python main.py
```

3. **Ensure requirements.txt is complete:**

```txt
requests==2.32.5
pytz==2025.2
apscheduler==3.11.2
fastapi==0.115.0
uvicorn==0.32.0
pydantic==2.10.6
```

### Step 2: Deploy to Railway

1. **Sign up**: Go to https://railway.app
2. **New Project**: Click "New Project"
3. **Deploy from GitHub**:
   - Connect your GitHub account
   - Select your repository
4. **Auto-Configuration**: Railway automatically:
   - Detects Python
   - Installs from requirements.txt
   - Runs your app
5. **Get URL**: Railway provides a URL like `https://your-app.railway.app`

### Step 3: Configure Environment (Optional)

If you want to use environment variables instead of hardcoded config:

1. In Railway dashboard, go to "Variables"
2. Add:
   - `LEADPIER_USERNAME=hello@shaktallc.com`
   - `LEADPIER_PASSWORD=Shakta123!`
   - `PORT=8000`

### Step 4: Monitor

- Check logs in Railway dashboard
- Your scheduler will run every 10 minutes
- Access API at `https://your-app.railway.app/health`

---

## 🆓 Alternative: Render.com (Free)

### Step 1: Prepare

Same .gitignore and requirements.txt as above.

### Step 2: Deploy

1. **Sign up**: Go to https://render.com
2. **New Web Service**: Click "New" → "Web Service"
3. **Connect Repo**: Connect your GitHub repository
4. **Configure**:
   - **Name**: leadpier-sync
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. **Create Web Service**

### Step 3: Access

- URL: `https://leadpier-sync.onrender.com`
- Note: Free tier may sleep after 15 min inactivity

---

## 🐳 Option 3: Docker + Any Platform

Deploy as a Docker container to DigitalOcean, AWS, or Google Cloud.

### Create Dockerfile:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

### Create .dockerignore:

```
__pycache__/
*.pyc
.env
.venv/
venv/
logs/
*.log
.git/
.gitignore
README.md
```

### Deploy:

```bash
# Build
docker build -t leadpier-sync .

# Run locally
docker run -p 8000:8000 leadpier-sync

# Push to Docker Hub
docker tag leadpier-sync yourusername/leadpier-sync
docker push yourusername/leadpier-sync
```

Then deploy to:

- **DigitalOcean App Platform**
- **AWS ECS/Fargate**
- **Google Cloud Run**
- **Azure Container Instances**

---

## 🔄 If You Insist on Vercel (NOT Recommended)

You'll need to **completely restructure** your application:

### Changes Required:

1. **Remove APScheduler** - Use Vercel Cron Jobs instead (Pro plan required)
2. **Make Stateless** - Move token to database (MongoDB Atlas, PlanetScale)
3. **Separate API & Worker**:
   - API: FastAPI endpoints only (Vercel)
   - Worker: Scheduler on separate service (Railway/Render)

### Create vercel.json:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ],
  "crons": [
    {
      "path": "/trigger",
      "schedule": "*/10 * * * *"
    }
  ]
}
```

### Modified main.py (Vercel version):

Remove all scheduler code, keep only API endpoints. The cron job will call `/trigger` every 10 minutes.

**Issues**:

- Cron jobs require Pro plan ($20/month)
- Each trigger is a separate function call (cold starts)
- No persistent logs
- Need external database for tokens

---

## 📊 Comparison

| Platform           | Cost              | Scheduler  | Persistent Storage | Difficulty    | Recommended         |
| ------------------ | ----------------- | ---------- | ------------------ | ------------- | ------------------- |
| **Railway**        | $5/mo free credit | ✅ Yes     | ✅ Yes             | ⭐ Easy       | ✅ **Best**         |
| **Render**         | Free tier         | ✅ Yes     | ✅ Yes             | ⭐ Easy       | ✅ Good             |
| **PythonAnywhere** | Free tier         | ✅ Yes     | ✅ Yes             | ⭐⭐ Medium   | ✅ Good             |
| **Heroku**         | $5/mo minimum     | ✅ Yes     | ✅ Yes             | ⭐ Easy       | ✅ Good             |
| **Vercel**         | Free (Pro $20)    | ❌ Limited | ❌ No              | ⭐⭐⭐⭐ Hard | ❌ **Not Suitable** |

---

## 🚀 Quick Start: Railway (30 seconds)

```bash
# 1. Install Railway CLI (optional)
npm i -g @railway/cli

# 2. Login
railway login

# 3. Initialize
railway init

# 4. Deploy
railway up

# 5. Get URL
railway domain
```

Or just use the Railway web interface - no CLI needed!

---

## 🔐 Security Recommendations

Before deploying:

1. **Use Environment Variables**:

   ```python
   import os
   LEADPIER_USERNAME = os.getenv('LEADPIER_USERNAME', 'hello@shaktallc.com')
   LEADPIER_PASSWORD = os.getenv('LEADPIER_PASSWORD', 'Shakta123!')
   ```

2. **Add .env file** (don't commit to git):

   ```env
   LEADPIER_USERNAME=hello@shaktallc.com
   LEADPIER_PASSWORD=Shakta123!
   ```

3. **Update .gitignore**:
   ```
   .env
   source.json
   logs/
   ```

---

## 📞 Support

Choose your platform:

- **Railway**: https://railway.app/help
- **Render**: https://render.com/docs
- **PythonAnywhere**: https://help.pythonanywhere.com

---

## ✅ Recommended Action

**Deploy to Railway - it takes 2 minutes:**

1. Go to https://railway.app
2. Click "Start a New Project"
3. Click "Deploy from GitHub repo"
4. Select your repository
5. Done! Your app is live with the scheduler running.

Railway is **purpose-built** for apps like yours with background jobs.
