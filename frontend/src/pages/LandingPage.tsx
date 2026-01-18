import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();

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
        {/* Gradient Overlay for better text readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-blue-900/40 via-blue-900/20 to-blue-900/60" />
        <div className="absolute inset-0 bg-black/20" />
      </div>

      {/* Hero Section - Title Centered */}
      <div className="relative z-10 h-screen flex items-center justify-center px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="text-center -mt-20"
        >
          <h1 className="text-8xl text-white drop-shadow-2xl tracking-[0.3em] mb-8">
            village ai
          </h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.8 }}
            className="text-3xl text-white drop-shadow-lg mb-4 font-medium"
          >
           raising the elderly 
          </motion.p>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="text-xl text-white/90 drop-shadow-lg font-light"
          >
            Daily companion calls that detect patterns, mobilize care networks,
            <br />
            and ensure no one falls through the cracks
          </motion.p>

          {/* Demo Button */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.7, duration: 0.5, type: 'spring' }}
            className="mt-8"
          >
            <motion.button
              onClick={() => navigate('/demo')}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              className="backdrop-blur-md bg-white/20 hover:bg-white/30 text-white font-semibold px-8 py-4 rounded-full transition-all shadow-2xl border border-white/30 text-lg"
            >
              Demo
            </motion.button>
          </motion.div>
        </motion.div>
      </div>

      {/* Content Section - Scroll to reveal */}
      <div className="relative z-10 px-8 pb-32">
        <div className="max-w-6xl mx-auto">

          {/* How It Works Section */}
          <div className="mb-24">
            <h2 className="text-5xl font-bold text-white text-center mb-12">How It Works</h2>
            <div className="backdrop-blur-md bg-white/10 rounded-2xl p-12 border border-white/20 shadow-2xl">
              <div className="space-y-8">
                <div>
                  <h3 className="text-2xl font-semibold text-white mb-3">1. Daily Check-Ins</h3>
                  <p className="text-white/90 text-lg font-light">
                    Our AI companion initiates friendly, natural conversations with elderly individuals living alone.
                    These daily calls feel like chatting with a caring friend, not a clinical assessment.
                  </p>
                </div>
                <div>
                  <h3 className="text-2xl font-semibold text-white mb-3">2. Real-Time Analysis</h3>
                  <p className="text-white/90 text-lg font-light">
                    During conversations, we monitor biometric data including heart rate, respiratory patterns, and vocal
                    characteristics. Advanced AI analyzes emotional, mental, social, physical, and cognitive wellbeing.
                  </p>
                </div>
                <div>
                  <h3 className="text-2xl font-semibold text-white mb-3">3. Instant Response</h3>
                  <p className="text-white/90 text-lg font-light">
                    When concerns are detected, the system automatically mobilizes the elder's care network within 78 seconds.
                    Family, friends, and healthcare providers receive immediate alerts with actionable insights.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* The Village Section */}
          <div className="mb-24">
            <h2 className="text-5xl font-bold text-white text-center mb-12">What is The Village?</h2>
            <div className="backdrop-blur-md bg-white/10 rounded-2xl p-12 border border-white/20 shadow-2xl">
              <p className="text-white/90 text-lg font-light mb-6">
                The Village is your personalized care network—a group of trusted individuals who care about the elder's
                wellbeing. This includes family members, close friends, neighbors, and healthcare providers.
              </p>
              <p className="text-white/90 text-lg font-light mb-6">
                When our AI detects patterns of concern—changes in mood, speech patterns, cognitive function, or physical
                health—the Village is immediately notified. Each member receives context-aware alerts based on their
                relationship and role.
              </p>
              <p className="text-white/90 text-lg font-light">
                No one needs to shoulder the responsibility alone. The Village ensures collective care, rapid response,
                and peace of mind for everyone involved.
              </p>
            </div>
          </div>

          {/* Features Section */}
          <div className="mb-24">
            <h2 className="text-5xl font-bold text-white text-center mb-12">Key Features</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Vocal Analysis */}
              <div className="backdrop-blur-md bg-white/10 rounded-2xl p-8 border border-white/20 shadow-2xl">
                <h3 className="font-semibold text-2xl mb-4 text-white">Vocal Health Detection</h3>
                <p className="text-white/90 text-base font-light mb-4">
                  Our AI analyzes subtle changes in speech patterns, tone, pace, and vocal quality to detect early signs
                  of cognitive decline, depression, respiratory issues, and neurological conditions.
                </p>
                <ul className="text-white/80 text-sm font-light space-y-2">
                  <li>• Speech hesitations and word-finding difficulties</li>
                  <li>• Vocal tremors and rhythm irregularities</li>
                  <li>• Emotional tone and affect changes</li>
                  <li>• Respiratory rate from breathing patterns</li>
                </ul>
              </div>

              {/* Biometric Monitoring */}
              <div className="backdrop-blur-md bg-white/10 rounded-2xl p-8 border border-white/20 shadow-2xl">
                <h3 className="font-semibold text-2xl mb-4 text-white">Real-Time Biometrics</h3>
                <p className="text-white/90 text-base font-light mb-4">
                  Continuous monitoring of vital signs during conversations without any wearable devices required.
                  Our technology extracts biometric data from voice and conversation patterns.
                </p>
                <ul className="text-white/80 text-sm font-light space-y-2">
                  <li>• Heart rate and heart rate variability</li>
                  <li>• Respiratory rate and rhythm regularity</li>
                  <li>• Stress and anxiety indicators</li>
                  <li>• Audio quality and clarity metrics</li>
                </ul>
              </div>

              {/* 5-Dimension Wellbeing */}
              <div className="backdrop-blur-md bg-white/10 rounded-2xl p-8 border border-white/20 shadow-2xl">
                <h3 className="font-semibold text-2xl mb-4 text-white">5-Dimension Wellbeing Analysis</h3>
                <p className="text-white/90 text-base font-light mb-4">
                  Comprehensive assessment across five critical dimensions of health, providing a holistic view
                  of the elder's wellbeing over time.
                </p>
                <ul className="text-white/80 text-sm font-light space-y-2">
                  <li>• Emotional: mood, affect, emotional stability</li>
                  <li>• Mental: cognitive function, memory, clarity</li>
                  <li>• Social: engagement, relationships, isolation</li>
                  <li>• Physical: mobility, energy, vital signs</li>
                  <li>• Cognitive: attention, processing, comprehension</li>
                </ul>
              </div>

              {/* Rapid Response */}
              <div className="backdrop-blur-md bg-white/10 rounded-2xl p-8 border border-white/20 shadow-2xl">
                <h3 className="font-semibold text-2xl mb-4 text-white">78-Second Alert System</h3>
                <p className="text-white/90 text-base font-light mb-4">
                  When concerns are detected, the entire care network is mobilized within 78 seconds with
                  actionable insights and recommended interventions.
                </p>
                <ul className="text-white/80 text-sm font-light space-y-2">
                  <li>• Automatic alert prioritization by urgency</li>
                  <li>• Context-aware notifications per relationship</li>
                  <li>• Suggested actions based on concern type</li>
                  <li>• Direct communication channels activated</li>
                </ul>
              </div>

            </div>
          </div>

        </div>
      </div>

      {/* Footer - Positioned at bottom */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.8 }}
        className="fixed bottom-8 left-0 right-0 text-center text-sm text-white/60 font-light z-20"
      >
        NexHacks 2026 · Built for elderly wellbeing
      </motion.div>
    </div>
  );
}
