#!/bin/bash

echo "🚂 Deploying The Village Backend to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install it first:"
    echo "curl -fsSL https://railway.app/install.sh | sh"
    exit 1
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway. Run: railway login"
    exit 1
fi

# Initialize Railway project if not already done
if [ ! -f "railway.toml" ]; then
    echo "📝 Initializing Railway project..."
    railway init --name "the-village-backend"
fi

# Set environment variables (you'll need to fill these in)
echo "🔧 Setting environment variables..."
echo "⚠️  Make sure to set your actual API keys!"
railway variables set SUPABASE_URL="your-supabase-url"
railway variables set SUPABASE_ANON_KEY="your-anon-key"
railway variables set SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
railway variables set LIVEKIT_API_KEY="your-livekit-api-key"
railway variables set LIVEKIT_API_SECRET="your-livekit-api-secret"
railway variables set LIVEKIT_URL="your-livekit-url"
railway variables set GOOGLE_API_KEY="your-google-api-key"
railway variables set ASSEMBLYAI_API_KEY="your-assemblyai-key"
railway variables set CARTESIA_API_KEY="your-cartesia-key"
railway variables set VITAL_AUDIO_API_KEY="your-vital-audio-key"
railway variables set S3_ENDPOINT="your-s3-endpoint"
railway variables set S3_ACCESS_KEY="your-s3-access-key"
railway variables set S3_SECRET="your-s3-secret"
railway variables set S3_BUCKET="audio_files"
railway variables set ENABLE_RECORDING="true"

# Deploy
echo "🚀 Deploying to Railway..."
railway up

# Get the deployment URL
echo "📍 Deployment URL:"
railway domain

echo "✅ Deployment complete!"
echo "📋 Don't forget to:"
echo "   1. Run the database schema in Supabase"
echo "   2. Upload the Parkinson's model file"
echo "   3. Test the API endpoints"