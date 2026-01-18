import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { DemoConfig as DemoConfigType, VillageMember } from '../types';
import { DEFAULT_VILLAGE_MEMBERS, DEFAULT_ELDER_PHONE, DEFAULT_MY_PHONE } from '../data/margaret';

export default function DemoConfigPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'all-to-me' | 'custom'>('all-to-me');
  const [myPhone, setMyPhone] = useState(DEFAULT_MY_PHONE);
  const [elderPhone, setElderPhone] = useState(DEFAULT_ELDER_PHONE);
  const [villageMembers, setVillageMembers] = useState<VillageMember[]>(DEFAULT_VILLAGE_MEMBERS);

  const handleToggleMember = (id: string) => {
    setVillageMembers(prev =>
      prev.map(member =>
        member.id === id ? { ...member, enabled: !member.enabled } : member
      )
    );
  };

  const handleUpdatePhone = (id: string, phone: string) => {
    setVillageMembers(prev =>
      prev.map(member =>
        member.id === id ? { ...member, phone } : member
      )
    );
  };

  const handleUseMyPhone = () => {
    setMode('all-to-me');
    setElderPhone(myPhone);
    setVillageMembers(prev =>
      prev.map(member => ({ ...member, phone: myPhone }))
    );
  };

  const handleStartDemo = () => {
    console.log('🚀 [DemoConfig] START DEMO button clicked');
    console.log('📋 [DemoConfig] Mode:', mode);
    console.log('📋 [DemoConfig] Elder phone:', elderPhone);
    console.log('📋 [DemoConfig] My phone:', myPhone);
    console.log('📋 [DemoConfig] Village members:', villageMembers);

    const config: DemoConfigType = {
      mode,
      myPhone: mode === 'all-to-me' ? myPhone : undefined,
      elder: {
        name: 'Margaret Chen',
        age: 78,
        phone: elderPhone,
      },
      village: villageMembers.filter(m => m.enabled),
    };

    console.log('💾 [DemoConfig] Saving config to localStorage:', config);
    // Store config in localStorage and navigate
    localStorage.setItem('demoConfig', JSON.stringify(config));
    console.log('✅ [DemoConfig] Config saved, navigating to /dashboard');
    navigate('/dashboard');
  };

  const isValid = () => {
    if (mode === 'all-to-me') {
      return myPhone.length >= 10;
    }
    return elderPhone.length >= 10 && villageMembers.filter(m => m.enabled).length >= 1;
  };

  const enabledCount = villageMembers.filter(m => m.enabled).length;

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Video Background */}
      <div className="fixed inset-0 z-0">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover"
        >
          <source src="/clouds.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-blue-900/40 via-blue-900/20 to-blue-900/60" />
        <div className="absolute inset-0 bg-black/20" />
      </div>

      <div className="relative z-10 px-8 py-12">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <h1 className="text-6xl font-bold text-white tracking-[0.2em] mb-4">village ai</h1>
            <p className="text-xl text-white/90 font-light">
              AI-powered holistic wellbeing system for elderly care
            </p>
            <p className="text-sm text-white/70 mt-2 font-light">
              Daily companion calls that detect patterns and mobilize care networks
            </p>
          </motion.div>

          {/* Demo Configuration Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="backdrop-blur-md bg-white/10 rounded-2xl shadow-2xl p-8 border border-white/20"
          >
            <h2 className="text-2xl font-semibold text-white mb-6">Demo Configuration</h2>

          {/* Quick Setup - Use My Phone */}
          <div className="mb-8">
            <label className="block text-sm font-medium mb-3 text-white/80 font-light">
              Quick Setup
            </label>
            <div className="backdrop-blur-sm bg-blue-400/20 border border-blue-300/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  checked={mode === 'all-to-me'}
                  onChange={() => setMode('all-to-me')}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="font-medium text-white mb-2">Use My Phone for All Calls</div>
                  <p className="text-sm text-white/70 mb-3 font-light">
                    All calls (elder + village) will be placed to your phone number
                  </p>
                  {mode === 'all-to-me' && (
                    <input
                      type="tel"
                      value={myPhone}
                      onChange={(e) => setMyPhone(e.target.value)}
                      onBlur={handleUseMyPhone}
                      placeholder="+1-___-___-____"
                      className="w-full backdrop-blur-sm bg-white/10 border border-white/30 rounded px-4 py-2 focus:outline-none focus:border-white/50 text-white placeholder-white/40"
                    />
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Custom Configuration */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <input
                type="radio"
                checked={mode === 'custom'}
                onChange={() => setMode('custom')}
              />
              <label className="text-sm font-medium text-white/80 font-light">
                ─── OR Configure Custom Numbers ───
              </label>
            </div>

            {mode === 'custom' && (
              <div className="space-y-6 pl-7">
                {/* Elder Phone */}
                <div>
                  <label className="block text-sm font-medium mb-2 text-white/90 font-light">
                    Elder: Margaret Chen, 78
                  </label>
                  <input
                    type="tel"
                    value={elderPhone}
                    onChange={(e) => setElderPhone(e.target.value)}
                    placeholder="+1-___-___-____"
                    className="w-full backdrop-blur-sm bg-white/10 border border-white/30 rounded px-4 py-2 focus:outline-none focus:border-white/50 text-white placeholder-white/40"
                  />
                  <p className="text-xs text-white/60 mt-1 font-light">*Required</p>
                </div>

                {/* Village Members */}
                <div>
                  <label className="block text-sm font-medium mb-3 text-white/90 font-light">
                    Village Network (minimum 1 member)
                  </label>
                  <p className="text-xs text-white/60 mb-4 font-light">
                    {enabledCount} member{enabledCount !== 1 ? 's' : ''} enabled
                  </p>

                  <div className="space-y-4">
                    {villageMembers.map((member) => (
                      <div
                        key={member.id}
                        className={`border rounded-lg p-4 transition-all ${
                          member.enabled
                            ? 'border-blue-300/40 backdrop-blur-sm bg-blue-400/20'
                            : 'border-white/20 backdrop-blur-sm bg-white/5'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            checked={member.enabled}
                            onChange={() => handleToggleMember(member.id)}
                            className="mt-1"
                          />
                          <div className="flex-1">
                            <div className="font-medium mb-1 text-white">
                              {member.name} ({member.relationship})
                            </div>
                            <p className="text-xs text-white/60 mb-2 font-light">
                              {member.notes}
                            </p>
                            {member.enabled && (
                              <input
                                type="tel"
                                value={member.phone}
                                onChange={(e) => handleUpdatePhone(member.id, e.target.value)}
                                placeholder="+1-___-___-____"
                                className="w-full backdrop-blur-sm bg-white/10 border border-white/30 rounded px-3 py-2 text-sm focus:outline-none focus:border-white/50 text-white placeholder-white/40"
                              />
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Start Demo Button */}
          <div className="text-center pt-4">
            <motion.button
              onClick={handleStartDemo}
              disabled={!isValid()}
              whileHover={isValid() ? { scale: 1.05 } : {}}
              whileTap={isValid() ? { scale: 0.95 } : {}}
              className={`px-8 py-4 rounded-full font-semibold text-lg transition-all ${
                isValid()
                  ? 'backdrop-blur-md bg-white/20 hover:bg-white/30 text-white shadow-2xl border border-white/30'
                  : 'backdrop-blur-md bg-white/5 text-white/30 cursor-not-allowed border border-white/10'
              }`}
            >
              START DEMO
            </motion.button>
            {!isValid() && (
              <p className="text-sm text-white/60 mt-3 font-light">
                {mode === 'custom' && enabledCount < 1
                  ? 'Enable at least 1 village member'
                  : 'Enter valid phone numbers'}
              </p>
            )}
          </div>
        </motion.div>

        {/* Info Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="mt-8 text-center space-y-2 text-sm text-white/60 font-light"
        >
          <p>Tip: Use your own phone numbers to test the system with real calls</p>
          <p>Features: Real-time biometrics · 5-dimension analysis · Village mobilization</p>
        </motion.div>
      </div>
      </div>
    </div>
  );
}
