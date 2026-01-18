import { useEffect, useRef } from 'react';
import { TranscriptLine as TranscriptLineType } from '../../types';
import TranscriptLine from './TranscriptLine';

interface LiveTranscriptProps {
  lines: TranscriptLineType[];
  isActive: boolean;
}

export default function LiveTranscript({ lines, isActive }: LiveTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  console.log('');
  console.log('🎨 [LiveTranscript] Component rendering');
  console.log('   Lines prop length:', lines.length);
  console.log('   Lines prop:', lines);
  console.log('   Is active:', isActive);

  useEffect(() => {
    console.log('   🔄 [LiveTranscript] Lines changed, scrolling...');
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  return (
    <div className="backdrop-blur-md bg-white/10 rounded-2xl p-6 border border-white/20 shadow-2xl h-[500px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Live Transcript</h3>
        {isActive && (
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></span>
            <span className="text-sm text-white/70 font-light">Recording</span>
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto pr-2 space-y-2 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent"
      >
        {lines.length === 0 ? (
          <div className="flex items-center justify-center h-full text-white/50 font-light">
            Waiting for conversation to start...
          </div>
        ) : (
          lines.map((line) => <TranscriptLine key={line.id} line={line} />)
        )}
      </div>
    </div>
  );
}
