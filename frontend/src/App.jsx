import { useState, useCallback, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import HeroInput from './components/HeroInput';
import NeuralSphere from './components/NeuralSphere';
import ResultsSection from './components/ResultsSection';
import { streamRanking, rankCandidates } from './api';

/**
 * Main App — wires HeroInput → NeuralSphere → ResultsSection
 * with SSE streaming for real-time pipeline status.
 */
export default function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState({});
  const [candidates, setCandidates] = useState([]);
  const [parsedJd, setParsedJd] = useState(null);
  const [error, setError] = useState('');

  // Determine the current view state based on application logic
  const viewState = useMemo(() => {
    if (candidates.length > 0) return 'results';
    if (isLoading) return 'processing';
    return 'landing';
  }, [isLoading, candidates.length]);

  const handleSubmit = useCallback(async (jobDescription, resumes) => {
    setIsLoading(true);
    setError('');
    setCandidates([]);
    setParsedJd(null);
    setAgentStatuses({});

    try {
      // Try SSE streaming first
      let resolved = false;
      const stages = ['intake', 'retrieval', 'scoring', 'interview_prep', 'bias_audit', 'merge'];

      const streamPromise = new Promise((resolve, reject) => {
        const cancel = streamRanking(
          jobDescription,
          resumes,
          // onStatus
          (statusUpdate) => {
            setAgentStatuses((prev) => ({
              ...prev,
              [statusUpdate.agent]: statusUpdate.status,
            }));
          },
          // onResult
          (result) => {
            resolved = true;
            // Mark all stages complete
            const allComplete = {};
            stages.forEach((s) => { allComplete[s] = 'completed'; });
            setAgentStatuses(allComplete);

            if (result.error) {
              reject(new Error(result.error));
            } else {
              resolve(result);
            }
          },
          // onError
          (err) => {
            if (!resolved) reject(err);
          }
        );

        // Timeout fallback after 60s
        setTimeout(() => {
          if (!resolved) {
            cancel();
            reject(new Error('Request timed out'));
          }
        }, 60000);
      });

      // Try streaming, fall back to sync
      let result;
      try {
        result = await streamPromise;
      } catch (streamErr) {
        console.warn('SSE streaming failed, falling back to sync:', streamErr);
        
        // Fall back to synchronous endpoint
        result = await rankCandidates(jobDescription, resumes);

        // Mark all stages complete
        const allComplete = {};
        stages.forEach((s) => { allComplete[s] = 'completed'; });
        setAgentStatuses(allComplete);
      }

      setCandidates(result.candidates || []);
      setParsedJd(result.parsed_jd || null);
    } catch (err) {
      console.error('Pipeline failed:', err);
      setError(err.message || 'An error occurred. Please try again.');

      // Mark current stage as error
      setAgentStatuses((prev) => {
        const updated = { ...prev };
        Object.keys(updated).forEach((key) => {
          if (updated[key] === 'running') updated[key] = 'error';
        });
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* 3D Background / Hero Element */}
      <NeuralSphere viewState={viewState} agentStatuses={agentStatuses} />

      {/* Main Content Area */}
      <main className="relative z-10 min-h-screen flex flex-col">
        {/* Landing / Processing State overlays */}
        <AnimatePresence mode="wait">
          {viewState !== 'results' && (
            <motion.div 
              key="hero"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50 }}
              className="flex-1 flex flex-col items-center justify-end pb-12 px-4"
            >
              {/* Processing Overlay Labels */}
              {viewState === 'processing' && (
                 <div className="absolute top-8 left-1/2 -translate-x-1/2 text-center pointer-events-none">
                   <h2 className="text-hm-text text-xl tracking-[0.2em] font-mono opacity-80 uppercase">
                     HireMind
                   </h2>
                   <div className="mt-8 flex items-center gap-4 text-xs font-mono">
                     <span className="text-hm-cyan animate-pulse">●</span>
                     <span className="text-hm-text-muted uppercase tracking-wider">
                       Agents processing data...
                     </span>
                   </div>
                 </div>
              )}

              {/* Input Form (hidden while processing) */}
              <div className={`transition-all duration-500 w-full ${viewState === 'processing' ? 'opacity-0 pointer-events-none translate-y-12' : 'opacity-100'}`}>
                <HeroInput onSubmit={handleSubmit} isLoading={isLoading} />
              </div>
            </motion.div>
          )}

          {/* Results State */}
          {viewState === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5, duration: 0.8 }}
              className="flex-1 w-full pt-24" // padding top to clear the miniaturized sphere
            >
              {/* Header next to the miniaturized sphere */}
              <div className="max-w-5xl mx-auto px-4 flex justify-between items-end border-b border-hm-surface-border pb-4 mb-8 pl-32">
                 <div>
                   <h1 className="text-lg font-mono tracking-[0.2em] uppercase text-hm-text">HireMind</h1>
                   <p className="text-xs text-hm-text-muted mt-1">{candidates.length} candidates ranked</p>
                 </div>
                 <div className="text-xs font-mono text-hm-text-muted flex gap-4">
                   <span>AVG SCORE: {(candidates.reduce((a,c) => a + c.score, 0) / candidates.length).toFixed(1)}</span>
                   <span>|</span>
                   <span>TOP MATCH: {candidates[0]?.score}</span>
                   <span>|</span>
                   <span className="text-hm-success">AGENTS: 5/5 ✓</span>
                 </div>
              </div>

              {error && (
                <div className="max-w-5xl mx-auto px-4 mb-8">
                  <div className="glass-panel p-4 border-hm-danger/30 text-hm-danger text-sm font-mono">
                    ⚠ {error}
                  </div>
                </div>
              )}

              <ResultsSection candidates={candidates} parsedJd={parsedJd} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
