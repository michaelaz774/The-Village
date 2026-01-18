# The Village Backend - Railway Deployment

This is the FastAPI backend for The Village - an AI companion system for elderly care.

## 🚀 Railway Deployment

### Prerequisites
- Railway account
- Supabase project
- LiveKit account
- API keys for various services

### Environment Variables Required

Set these in your Railway project environment variables:

#### Supabase Configuration
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

#### LiveKit Configuration
```
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
```

#### S3/Storage Configuration
```
S3_ENDPOINT=https://your-project.supabase.co/storage/v1/s3
S3_ACCESS_KEY=your-s3-access-key
S3_SECRET=your-s3-secret
S3_BUCKET=audio_files
S3_REGION=us-east-1
```

#### AI Service Keys
```
GOOGLE_API_KEY=your-google-api-key
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
CARTESIA_API_KEY=your-cartesia-api-key
VITAL_AUDIO_API_KEY=your-vital-audio-api-key
```

#### Application Settings
```
ENABLE_RECORDING=true
```

### Database Setup

Run the SQL schema in your Supabase SQL Editor:

```sql
-- Copy and paste the contents of schema_simple.sql
```

### Parkinson's ML Model

Place the trained Parkinson's model file `best_pd_model.pkl` in the `backend/parkinson/` directory.

### Deployment Steps (Railway UI)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Railway deployment"
   git push origin main
   ```

2. **Railway Dashboard:**
   - Go to [railway.app](https://railway.app)
   - "Start a New Project" → "Deploy from GitHub repo"
   - Select your repository
   - **Important:** Set "Root Directory" to `backend/`

3. **Set Environment Variables:**
   In Railway Variables tab, add all required variables from the list above.

4. **Deploy:**
   - Railway will auto-detect Python and use `railway.toml`
   - Click "Deploy" and watch the build logs

### API Endpoints

Once deployed, your API will be available at:
- Health check: `GET /health`
- Elderly management: `GET/POST /elderly`
- Call management: `POST /start_call`
- Biomarkers: `POST /get_biomarkers`
- Parkinson's detection: `POST /detect_parkinson_from_recording`

### Monitoring

Check Railway logs for:
- Application startup
- Call processing
- Background task execution
- API requests/responses

### Troubleshooting

**Common Issues:**

1. **Missing Environment Variables:**
   - Check Railway dashboard for unset variables
   - All API keys must be set

2. **Database Connection:**
   - Verify Supabase URL and keys
   - Run schema SQL in Supabase

3. **Audio Processing:**
   - Ensure Parkinson's model file is included
   - Check ffmpeg installation in container

4. **LiveKit Connection:**
   - Verify LiveKit credentials
   - Check WebSocket connectivity

### Support

For issues with Railway deployment, check:
- Railway documentation: https://docs.railway.app/
- Railway status: https://railway.app/status
- Railway Discord community