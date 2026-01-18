
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Try loading from .env.local first, then .env
load_dotenv(".env.local")
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
# Try service key first (for server-side), fall back to anon key (for client-side)
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

supabase: Client = None

if url and key:
    try:
        supabase = create_client(url, key)
        print(f"✅ Supabase client initialized with URL: {url}")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        supabase = None
else:
    print(f"❌ Supabase credentials not found in environment variables.")
    print(f"   SUPABASE_URL: {'✓' if url else '✗'}")
    print(f"   SUPABASE_SERVICE_KEY: {'✓' if os.environ.get('SUPABASE_SERVICE_KEY') else '✗'}")
