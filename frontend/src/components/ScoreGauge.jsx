import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

/**
 * Animated circular SVG score gauge with violet-to-cyan gradient.
 * Animates from 0 to the target score on mount.
 */
export default function ScoreGauge({ score = 0, size = 100, strokeWidth = 10, delay = 0 }) {
  const [displayScore, setDisplayScore] = useState(0);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(score, 100) / 100;
  const offset = circumference * (1 - progress);
  const center = size / 2;

  // Animate the number count-up
  useEffect(() => {
    const duration = 1500; // ms
    const startTime = Date.now() + delay;
    let animFrame;

    const tick = () => {
      const elapsed = Date.now() - startTime;
      if (elapsed < 0) {
        animFrame = requestAnimationFrame(tick);
        return;
      }
      const t = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayScore(Math.round(eased * score));

      if (t < 1) {
        animFrame = requestAnimationFrame(tick);
      }
    };

    animFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrame);
  }, [score, delay]);

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.5, delay: delay / 1000 }}
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="transform -rotate-90">
        <defs>
          <linearGradient id={`gauge-grad-${score}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#7C3AED" />
            <stop offset="100%" stopColor="#22D3EE" />
          </linearGradient>
          
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke="rgba(124, 58, 237, 0.15)"
          strokeWidth={strokeWidth}
          fill="none"
        />

        {/* Animated progress arc with glow */}
        <motion.circle
          cx={center}
          cy={center}
          r={radius}
          stroke={`url(#gauge-grad-${score})`}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          filter="url(#glow)"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, delay: delay / 1000, ease: 'easeOut' }}
        />
      </svg>

      {/* Score number */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono font-bold leading-none text-hm-text"
          style={{ fontSize: size * 0.35 }}
        >
          {displayScore}
        </span>
        <span
          className="font-mono text-hm-text-muted uppercase tracking-[0.2em] mt-1"
          style={{ fontSize: size * 0.1 }}
        >
          score
        </span>
      </div>
    </motion.div>
  );
}
