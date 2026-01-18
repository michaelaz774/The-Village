# ✅ Railway Deployment Checklist

## Pre-Deployment
- [ ] Push code to GitHub repository
- [ ] Ensure `backend/parkinson/best_pd_model.pkl` exists
- [ ] Test locally: `uvicorn main:app --reload`
- [ ] Verify all API keys and credentials

## Railway Setup
- [ ] Create Railway account at [railway.app](https://railway.app)
- [ ] Connect GitHub repository
- [ ] **CRITICAL:** Set Root Directory to `backend/` (click "Add Root Directory" in Railway)

## Environment Variables (Railway Dashboard → Variables)
- [ ] `SUPABASE_URL` - Your Supabase project URL
- [ ] `SUPABASE_ANON_KEY` - Supabase anon key
- [ ] `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- [ ] `LIVEKIT_API_KEY` - LiveKit API key
- [ ] `LIVEKIT_API_SECRET` - LiveKit API secret
- [ ] `LIVEKIT_URL` - LiveKit WebSocket URL
- [ ] `GOOGLE_API_KEY` - Google AI API key
- [ ] `ASSEMBLYAI_API_KEY` - AssemblyAI API key
- [ ] `CARTESIA_API_KEY` - Cartesia API key
- [ ] `VITAL_AUDIO_API_KEY` - Vital Audio API key
- [ ] `S3_ENDPOINT` - Supabase storage endpoint
- [ ] `S3_ACCESS_KEY` - Supabase storage access key
- [ ] `S3_SECRET` - Supabase storage secret
- [ ] `S3_BUCKET` - Set to `audio_files`
- [ ] `ENABLE_RECORDING` - Set to `true`

## Database Setup
- [ ] Run `backend/schema_simple.sql` in Supabase SQL Editor
- [ ] Verify tables created: `elderly`, `calls`
- [ ] Check sample data inserted

## Parkinson's Model
- [ ] Upload `best_pd_model.pkl` to Supabase Storage `audio_files/models/`
- [ ] Or ensure it's in `backend/parkinson/` directory

## Deployment
- [ ] Click "Deploy" in Railway dashboard
- [ ] Monitor build logs for errors
- [ ] Wait for "Deployment successful"
- [ ] Copy the generated URL

## Testing
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /elderly` returns sample elderly data
- [ ] Parkinson's model loads without errors

## Post-Deployment
- [ ] Update frontend with new API URL
- [ ] Test call functionality
- [ ] Monitor logs for any runtime errors
- [ ] Set up monitoring/alerts if needed

## Common Issues
- [ ] **Build fails**: Check Python dependencies in `requirements.txt`
- [ ] **Runtime errors**: Verify environment variables are set correctly
- [ ] **Database errors**: Ensure schema was run in Supabase
- [ ] **Model errors**: Verify `best_pd_model.pkl` is accessible
- [ ] **WebSocket errors**: Expected - frontend needs separate deployment

---
🎉 **Congratulations! Your AI companion system is now live on Railway!**