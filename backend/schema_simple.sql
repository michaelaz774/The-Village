-- Simplified Schema for The Village
-- Run this in your Supabase SQL Editor

-- ============================================================================
-- ELDERLY TABLE
-- ============================================================================

DROP TABLE IF EXISTS elderly CASCADE;
CREATE TABLE elderly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    phone_number TEXT NOT NULL,
    medical_conditions TEXT,  -- Simple text field for conditions
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CALLS TABLE
-- ============================================================================

DROP TABLE IF EXISTS calls CASCADE;
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    elderly_id UUID NOT NULL REFERENCES elderly(id) ON DELETE CASCADE,
    
    -- Call timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('ringing', 'in_progress', 'completed', 'failed')),
    
    -- Room info from LiveKit
    room_name TEXT NOT NULL,
    
    -- Recording (S3 path)
    recording_path TEXT,  -- e.g., "recordings/room_name_20260118_123456.mp3"
    
    -- Transcript (stored as JSONB array)
    transcript JSONB DEFAULT '[]'::jsonb,  -- [{"timestamp": "...", "speaker": "user/agent", "text": "..."}]
    
    -- Summary (AI-generated summary of the conversation)
    summary TEXT,
    
    -- Biomarkers (stored as JSONB)
    biomarkers JSONB,  -- {"heartRate": 72, "heartRateVariability": 45, ...}

    -- Parkinson's detection (stored as JSONB)
    parkinson_detection JSONB,  -- {"disease": "Parkinson", "confidence": 0.85, "message": "...", ...}

    created_at TIMESTAMPTZ DEFAULT NOW()
);

DROP INDEX IF EXISTS idx_calls_elderly;
CREATE INDEX idx_calls_elderly ON calls(elderly_id);

DROP INDEX IF EXISTS idx_calls_started;
CREATE INDEX idx_calls_started ON calls(started_at DESC);

DROP INDEX IF EXISTS idx_calls_room_name;
CREATE INDEX idx_calls_room_name ON calls(room_name);

-- ============================================================================
-- AUTO-UPDATE TIMESTAMP
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_elderly_updated_at ON elderly;
CREATE TRIGGER update_elderly_updated_at BEFORE UPDATE ON elderly
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE elderly ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;

-- Allow all for service role (for hackathon)
CREATE POLICY "Allow all for service role" ON elderly FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON calls FOR ALL USING (true);

-- ============================================================================
-- SAMPLE DATA (Optional)
-- ============================================================================

-- Insert a sample elderly person
INSERT INTO elderly (name, age, phone_number, medical_conditions)
VALUES 
    ('Margaret Johnson', 78, '+16159273395', 'Hypertension, Mild Arthritis'),
    ('Robert Smith', 82, '+14155551234', 'Diabetes Type 2, Heart Condition');
