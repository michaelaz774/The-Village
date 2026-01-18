import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  DemoConfig,
  Elder,
  CallSession,
  WellbeingAssessment,
  Concern,
  VillageAction,
  ProfileFact,
  TranscriptLine,
  WSEvent,
} from '../types';
import { api } from '../lib/api';
import { useWebSocket } from '../hooks/useWebSocket';

// Import all components
import DashboardLayout from '../components/layout/DashboardLayout';
import ElderProfileCard from '../components/elder/ElderProfileCard';
import CallPanel from '../components/call/CallPanel';
import LiveTranscript from '../components/call/LiveTranscript';
import ResponseTimer from '../components/call/ResponseTimer';
import WellbeingDashboard from '../components/wellbeing/WellbeingDashboard';
import ConcernsPanel from '../components/concerns/ConcernsPanel';
import VillageGrid from '../components/village/VillageGrid';
import ActiveActions from '../components/village/ActiveActions';
import ProfileFacts from '../components/profile/ProfileFacts';
import CallSummaryModal from '../components/summary/CallSummaryModal';

export default function Dashboard() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [elder, setElder] = useState<Elder | null>(null);

  // Call state
  const [activeCall, setActiveCall] = useState<CallSession | null>(null);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Assessment state
  const [wellbeing, setWellbeing] = useState<WellbeingAssessment | null>(null);
  const [concerns, setConcerns] = useState<Concern[]>([]);
  const [profileFacts, setProfileFacts] = useState<ProfileFact[]>([]);

  // Village state
  const [villageActions, setVillageActions] = useState<VillageAction[]>([]);
  const [timerRunning, setTimerRunning] = useState(false);
  const [timerStartedAt, setTimerStartedAt] = useState<string | null>(null);

  // Summary modal
  const [showSummary, setShowSummary] = useState(false);

  // WebSocket connection
  const handleWebSocketMessage = useCallback((event: WSEvent) => {
    console.log('');
    console.log('🟠 [FRONTEND] WebSocket message received');
    console.log('   Event type:', event.type);
    console.log('   Event data:', event.data);
    console.log('   Current transcript length:', transcript.length);
    console.log('   Active call:', activeCall?.id);

    switch (event.type) {
      case 'call_started':
        console.log('   ✅ Processing call_started');
        console.log('Call started:', event.data);
        break;

      case 'call_status':
        console.log('   ✅ Processing call_status');
        if (activeCall) {
          setActiveCall({ ...activeCall, status: event.data.status });
        }
        break;

      case 'transcript_update':
        console.log('   ✅ Processing transcript_update');
        console.log('   Speaker:', event.data.speaker);
        console.log('   Text:', event.data.text?.substring(0, 50));
        console.log('   Transcript line ID:', event.data.id);
        setTranscript((prev) => {
          // Deduplicate: only add if this ID doesn't already exist
          if (prev.some(line => line.id === event.data.id)) {
            console.log('   ⚠️  Duplicate transcript line detected, skipping');
            return prev;
          }
          const newTranscript = [...prev, event.data];
          console.log('   📊 New transcript length:', newTranscript.length);
          return newTranscript;
        });
        break;

      case 'wellbeing_update':
        console.log('   ✅ Processing wellbeing_update');
        setWellbeing((prev) => (prev ? { ...prev, ...event.data } : null));
        break;

      case 'profile_update':
        console.log('   ✅ Processing profile_update');
        setProfileFacts((prev) => [...prev, event.data]);
        break;

      case 'concern_detected':
        console.log('   ✅ Processing concern_detected');
        setConcerns((prev) => [...prev, event.data]);
        // Start timer if action required
        if (event.data.action_required && !timerRunning) {
          setTimerRunning(true);
          setTimerStartedAt(new Date().toISOString());
        }
        break;

      case 'village_action_started':
        console.log('   ✅ Processing village_action_started');
        setVillageActions((prev) => [...prev, event.data]);
        break;

      case 'village_action_update':
        console.log('   ✅ Processing village_action_update');
        setVillageActions((prev) =>
          prev.map((action) =>
            action.id === event.data.id
              ? { ...action, status: event.data.status, response: event.data.response }
              : action
          )
        );
        break;

      case 'call_ended':
        console.log('   ✅ Processing call_ended');
        if (activeCall) {
          setActiveCall({ ...activeCall, summary: event.data.summary, status: 'completed' });
          setShowSummary(true);
        }
        setTimerRunning(false);
        break;

      default:
        console.log('   ⚠️  Unknown WebSocket event:', event);
    }
  }, [activeCall, timerRunning, transcript]);

  const { connectionStatus, send, isConnected } = useWebSocket({
    enabled: activeCall !== null, // Only connect when there's an active call
    onMessage: handleWebSocketMessage,
    onOpen: () => console.log('✅ WebSocket connected for active call'),
    onClose: () => console.log('❌ WebSocket disconnected'),
    onError: (error) => console.error('⚠️  WebSocket error:', error),
  });

  // Subscribe to call events when connection is established
  useEffect(() => {
    if (isConnected && activeCall) {
      console.log(`📡 Subscribing to call ${activeCall.id}`);
      send({ type: 'subscribe_call', call_id: activeCall.id });

      // Also subscribe to room_name if present (for agent transcript updates)
      if (activeCall.room_name && activeCall.room_name !== activeCall.id) {
        console.log(`📡 Also subscribing to room ${activeCall.room_name}`);
        send({ type: 'subscribe_call', call_id: activeCall.room_name });
      }
    }
  }, [isConnected, activeCall?.id, activeCall?.room_name, send]);

  // Load config on mount
  useEffect(() => {
    console.log('📱 [Dashboard] Component mounted, loading config from localStorage');
    const stored = localStorage.getItem('demoConfig');

    if (!stored) {
      console.log('❌ [Dashboard] No config found in localStorage, redirecting to /');
      navigate('/');
      return;
    }

    console.log('📦 [Dashboard] Raw stored config:', stored);
    const demoConfig = JSON.parse(stored) as DemoConfig;
    console.log('✅ [Dashboard] Parsed demoConfig:', demoConfig);
    setConfig(demoConfig);

    // Create a mock Elder object from DemoConfig
    const mockElder: Elder = {
      id: '5b7c7691-5a74-44f1-88f7-2eaa58657e98', // Margaret Johnson's UUID from Supabase
      name: demoConfig.elder.name,
      age: demoConfig.elder.age,
      phone: demoConfig.elder.phone,
      address: 'Pittsburgh, PA',
      profile: [],
      village: demoConfig.village,
      medical: {
        primary_doctor: 'Dr. Smith',
        practice_name: 'Family Practice',
        practice_phone: '+1-555-0100',
        medications: [],
        conditions: [],
      },
      wellbeing_baseline: {
        typical_mood: 'Generally positive',
        social_frequency: 'Weekly family contact',
        cognitive_baseline: 'Sharp, good memory',
        physical_limitations: [],
        known_concerns: [],
      },
    };

    console.log('👴 [Dashboard] Created mockElder:', mockElder);
    setElder(mockElder);
  }, [navigate]);

  const handleStartCall = async () => {
    console.log('🎬 [Dashboard] handleStartCall called');
    console.log('👴 [Dashboard] Elder object:', elder);

    if (!elder) {
      console.log('❌ [Dashboard] No elder object, aborting');
      return;
    }

    console.log('📞 [Dashboard] Starting call with:');
    console.log('   - Elder ID:', elder.id);
    console.log('   - Elder Phone:', elder.phone);
    console.log('   - Elder Name:', elder.name);

    setIsLoading(true);
    try {
      // Call the API FIRST to get the real call ID from backend
      console.log('🌐 [Dashboard] Calling API: api.startCall()');
      console.log('   Request: elder_id =', elder.id);
      console.log('   Request: phone_number =', elder.phone);

      const response = await api.startCall(elder.id, elder.phone);
      console.log('✅ [Dashboard] API call successful, got call session:', response);

      // Use the REAL call session from backend (with correct UUID)
      setActiveCall(response);
      setTranscript([]);
      setConcerns([]);
      setVillageActions([]);
      setWellbeing(null);

      console.log('📱 [Dashboard] Set active call with backend ID:', response.id);
    } catch (error) {
      console.error('Failed to start call:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEndCall = async () => {
    if (!activeCall) return;

    try {
      await api.endCall(activeCall.id);
      setActiveCall({ ...activeCall, status: 'completed' });
      setShowSummary(true);
    } catch (error) {
      console.error('Failed to end call:', error);
      // Still show summary even if API call fails
      setActiveCall({ ...activeCall, status: 'completed' });
      setShowSummary(true);
    }
  };

  if (!config || !elder) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <div className="fixed inset-0 z-0">
          <video autoPlay loop muted playsInline className="w-full h-full object-cover">
            <source src="/clouds.mp4" type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-gradient-to-b from-blue-900/40 via-blue-900/20 to-blue-900/60" />
          <div className="absolute inset-0 bg-black/20" />
        </div>

        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white/50 mx-auto mb-4"></div>
            <p className="text-white/90 text-lg font-light">Loading configuration...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <DashboardLayout
      elderName={elder.name}
      elderAge={elder.age}
      connectionStatus={connectionStatus}
      sidebar={
        <>
          <ActiveActions actions={villageActions} />
          <VillageGrid members={elder.village} activeActions={villageActions} />
          <ProfileFacts facts={profileFacts} />
        </>
      }
    >
      <div className="space-y-6">
        {/* Elder Profile */}
        <ElderProfileCard elder={elder} />

        {/* Call Controls */}
        <CallPanel
          activeCall={activeCall}
          onStartCall={handleStartCall}
          onEndCall={handleEndCall}
          isLoading={isLoading}
        />

        {/* Response Timer (only show when timer is running) */}
        {timerRunning && timerStartedAt && (
          <ResponseTimer
            running={timerRunning}
            startedAt={timerStartedAt}
            targetSeconds={78}
          />
        )}

        {/* Live Transcript (only show during active call) */}
        {activeCall && (
          <>
            {console.log('📺 [Dashboard] Rendering LiveTranscript with transcript:', transcript)}
            <LiveTranscript
              lines={transcript}
              isActive={activeCall.status === 'in_progress'}
            />
          </>
        )}

        {/* Wellbeing Dashboard */}
        <WellbeingDashboard
          assessment={wellbeing}
          isCallActive={activeCall?.status === 'in_progress'}
        />

        {/* Concerns Panel */}
        {concerns.length > 0 && <ConcernsPanel concerns={concerns} />}
      </div>

      {/* Call Summary Modal */}
      <CallSummaryModal
        summary={activeCall?.summary || null}
        isOpen={showSummary}
        onClose={() => setShowSummary(false)}
      />
    </DashboardLayout>
  );
}
