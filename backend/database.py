
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory (where this file is located)
backend_dir = Path(__file__).parent
load_dotenv(backend_dir / ".env.local")
load_dotenv(backend_dir / ".env")

# Try to import supabase, but gracefully handle if not installed
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("Info: Supabase module not installed. Running in demo mode without database.")
    SUPABASE_AVAILABLE = False
    Client = None

url: str = os.environ.get("SUPABASE_URL")
# Try service key first (for server-side), fall back to anon key (for client-side)
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

supabase: Client = None

if SUPABASE_AVAILABLE and url and key:
    try:
        supabase = create_client(url, key)
        print(f"✅ Supabase client initialized successfully with URL: {url}")
    except Exception as e:
        print(f"❌ Failed to initialize Supabase client: {e}")
        supabase = None
elif SUPABASE_AVAILABLE:
    print("ℹ️  Info: Supabase credentials not found. Running without database.")
    print(f"   SUPABASE_URL: {'✓' if url else '✗'}")
    print(f"   SUPABASE_SERVICE_KEY: {'✓' if os.environ.get('SUPABASE_SERVICE_KEY') else '✗'}")
else:
    print("ℹ️  Info: Supabase module not installed. Running in demo mode (no database connection)")
