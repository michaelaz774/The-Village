# 🚂 Railway UI Deployment Guide

## Step 1: Prepare Your Repository

### Option A: GitHub Integration (Recommended)
1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Ready for Railway deployment"
   git push origin main
   ```

### Option B: Direct Upload
- Railway can also deploy from local files, but GitHub is recommended

## Step 2: Create Railway Project

1. **Go to [Railway.app](https://railway.app)**
2. **Click "Start a New Project"**
3. **Choose "Deploy from GitHub repo"**
4. **Connect your GitHub account**
5. **Select your repository** (`your-username/the-village`)
6. **Choose the `backend/` directory** (if your repo has frontend too)

## Step 3: Configure Build Settings

Railway will auto-detect Python and use these files:
- `railway.toml` - Railway configuration
- `pyproject.toml` - Python project settings
- `requirements.txt` - Dependencies

## Step 4: Set Environment Variables

In Railway Dashboard → Your Project → Variables:

### Required Variables:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
LIVEKIT_URL=wss://your-server.livekit.cloud

GOOGLE_API_KEY=your-google-api-key
ASSEMBLYAI_API_KEY=your-assemblyai-key
CARTESIA_API_KEY=your-cartesia-key
VITAL_AUDIO_API_KEY=your-vital-audio-key

S3_ENDPOINT=https://your-project.supabase.co/storage/v1/s3
S3_ACCESS_KEY=your-s3-access-key
S3_SECRET=your-s3-secret
S3_BUCKET=audio_files

ENABLE_RECORDING=true
```

## Step 5: Database Setup

1. **Open Supabase Dashboard**
2. **Go to SQL Editor**
3. **Run the schema:**

```sql
-- Copy everything from backend/schema_simple.sql and run it
```

## Step 6: Upload Parkinson's Model

1. **In Supabase Dashboard → Storage**
2. **Create `audio_files` bucket** (if not exists)
3. **Upload `best_pd_model.pkl`** to a folder called `models/`
4. **Or include it in your repo** at `backend/parkinson/best_pd_model.pkl`

## Step 7: Deploy

1. **In Railway Dashboard, click "Deploy"**
2. **Watch the build logs** - it will install dependencies and start the app
3. **Wait for "Deployment successful"**

## Step 8: Get Your API URL

1. **In Railway Dashboard → Settings → Domains**
2. **Copy the generated URL** (e.g., `https://the-village-backend.up.railway.app`)

## Step 9: Test the Deployment

```bash
# Test health endpoint
curl https://your-railway-url.up.railway.app/health

# Test elderly endpoint
curl https://your-railway-url.up.railway.app/elderly
```

## Troubleshooting

### Build Fails
- **Check logs** in Railway dashboard
- **Missing dependencies?** Check `requirements.txt`
- **Python version?** Railway uses Python 3.12 by default

### Runtime Errors
- **Missing env vars?** Check Variables tab
- **Database connection?** Verify Supabase credentials
- **Model file?** Ensure `best_pd_model.pkl` is accessible

### WebSocket Issues
- **Expected:** Frontend WebSocket connections will fail until you deploy the frontend too
- **This is normal** - backend doesn't serve WebSocket endpoints

## 🎉 Success!

Once deployed, your API endpoints will be available:
- `GET /health` - Health check
- `GET /elderly` - List elderly users
- `POST /start_call` - Start a call
- `POST /get_biomarkers` - Analyze biomarkers
- `POST /detect_parkinson_from_recording` - Parkinson's detection

## Next Steps

1. **Deploy Frontend** to another Railway project
2. **Connect Frontend** to Backend API URL
3. **Set up LiveKit** server if needed
4. **Configure domain** if desired

## Support

- Railway Docs: https://docs.railway.app/
- Railway Status: https://railway.app/status
- Railway Community: https://discord.gg/railway