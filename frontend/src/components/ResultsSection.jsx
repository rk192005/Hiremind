import { motion } from 'framer-motion';
import CandidateCard from './CandidateCard';

/**
 * Results section — list of ranked candidate cards.
 */
export default function ResultsSection({ candidates = [], parsedJd = null }) {
  if (candidates.length === 0) return null;

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="w-full max-w-5xl mx-auto px-4 pb-16"
    >
      {/* Candidate cards */}
      <div className="space-y-4">
        {candidates.map((candidate, index) => (
          <CandidateCard
            key={candidate.name + index}
            candidate={candidate}
            index={index}
          />
        ))}
      </div>
    </motion.section>
  );
}
