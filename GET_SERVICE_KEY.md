# 🔑 Getting Your Supabase Service Role Key

## The Problem

Your `.env` file has:
```
SUPABASE_SERVICE_KEY=sb_publishable_PyDLq3AKFPtLJEIHycOWcQ_JUjPEAri
```

This is a **publishable/anon key** (notice the `sb_publishable_` prefix), NOT a service role key.

## How to Get the Service Role Key

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project: **vkhklctjekmtcwltjapc** (The Village)
3. Click on **Settings** (⚙️ icon in the left sidebar)
4. Click on **API** 
5. Scroll down to **Project API keys**
6. Copy the **`service_role`** key (NOT the `anon` key)

**IMPORTANT**: The service role key:
- Usually starts with `eyJ...` (it's a JWT token)
- Is much longer than the anon key
- Should be kept SECRET (never commit to git)
- Has full access to bypass Row Level Security (RLS)

## Update Your .env File

Replace this line in your `.env`:
```bash
# OLD (this is the anon/publishable key)
SUPABASE_SERVICE_KEY=sb_publishable_PyDLq3AKFPtLJEIHycOWcQ_JUjPEAri

# NEW (should be your service_role key from Supabase dashboard)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdX...
```

## After Updating

1. Save your `.env` file
2. Restart your FastAPI server (Ctrl+C and rerun)
3. Try the call again:
   ```bash
   curl -X POST http://localhost:8000/start_call \
     -H "Content-Type: application/json" \
     -d '{"elderly_id": "YOUR_ID"}'
   ```

## Why Service Role Key?

- **Anon Key**: For client-side apps, limited by Row Level Security (RLS)
- **Service Role Key**: For server-side apps, bypasses RLS, full access

Since your backend needs to read/write to the database on behalf of users, you need the service role key.
