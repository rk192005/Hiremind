import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, MessageSquare, ShieldCheck, AlertTriangle, CheckCircle2 } from 'lucide-react';
import ScoreGauge from './ScoreGauge';

/**
 * Individual candidate result card with score gauge, expandable tabs.
 */
export default function CandidateCard({ candidate, index = 0 }) {
  const [activeTab, setActiveTab] = useState(null); // 'justification' | 'interview' | 'bias' | null

  const {
    rank = 0,
    name = 'Unknown',
    score = 0,
    skills = [],
    experience_years = 0,
    education = '',
    summary = '',
    justification = '',
    interview_questions = [],
    bias_audit = {},
    score_breakdown = {},
  } = candidate;

  const toggleTab = (tab) => {
    setActiveTab(activeTab === tab ? null : tab);
  };

  const biasRiskColor = {
    low: 'text-hm-success',
    medium: 'text-hm-warning',
    high: 'text-hm-danger',
  };

  const biasRiskBg = {
    low: 'bg-hm-success/10 border-hm-success/30',
    medium: 'bg-hm-warning/10 border-hm-warning/30',
    high: 'bg-hm-danger/10 border-hm-danger/30',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className={`glass-panel p-5 md:p-6 relative overflow-hidden ${rank === 1 ? 'border-l-[3px] border-l-hm-cyan shadow-[-10px_0_30px_rgba(34,211,238,0.1)]' : ''}`}
    >
      <div className="flex flex-col md:flex-row items-start gap-6">
        {/* Score gauge */}
        <div className="flex-shrink-0 self-center md:self-start pt-2">
          <ScoreGauge score={score} size={80} strokeWidth={8} delay={index * 150} />
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0 w-full">
          {/* Header row */}
          <div className="flex items-start justify-between gap-3 mb-3">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-sm font-mono font-bold text-hm-text-muted">
                  #{rank}
                </span>
                <h3 className="text-xl font-bold text-hm-text">{name}</h3>
              </div>
              <div className="flex flex-wrap gap-2 text-sm text-hm-text-muted">
                <span>{experience_years} yrs exp</span>
                {education && (
                  <>
                    <span className="text-hm-surface-border">•</span>
                    <span>{education}</span>
                  </>
                )}
              </div>
            </div>

            {/* Score breakdown mini */}
            <div className="hidden lg:flex gap-3 text-[10px] font-mono text-hm-text-muted">
              <div className="text-center">
                <div className="text-hm-cyan">{(score_breakdown.semantic_similarity * 100 || 0).toFixed(0)}%</div>
                <div>SEMANTIC</div>
              </div>
              <div className="text-center">
                <div className="text-hm-violet">{(score_breakdown.skill_overlap * 100 || 0).toFixed(0)}%</div>
                <div>SKILLS</div>
              </div>
              <div className="text-center">
                <div className="text-hm-success">{(score_breakdown.experience_match * 100 || 0).toFixed(0)}%</div>
                <div>EXP</div>
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="flex flex-wrap gap-2 mb-3">
            {skills.slice(0, 8).map((skill) => (
              <span
                key={skill}
                className="px-2 py-0.5 rounded-full bg-hm-bg/60 border border-hm-surface-border text-xs font-sans text-hm-violet"
              >
                {skill}
              </span>
            ))}
            {skills.length > 8 && (
              <span className="px-2 py-0.5 text-xs text-hm-text-muted font-mono">
                +{skills.length - 8} MORE
              </span>
            )}
          </div>

          {/* Justification preview (used instead of summary in new design) */}
          {justification && (
            <p className="text-sm text-hm-text-muted leading-relaxed mb-4 line-clamp-2">
              {justification}
            </p>
          )}

          {/* Tab buttons */}
          <div className="flex flex-wrap gap-2">
            {interview_questions.length > 0 && (
              <TabButton
                label="Interview Questions"
                icon={<MessageSquare className="w-3.5 h-3.5" />}
                isActive={activeTab === 'interview'}
                onClick={() => toggleTab('interview')}
                color="violet"
              />
            )}
            <TabButton
              label="Bias Audit"
              icon={<ShieldCheck className="w-3.5 h-3.5" />}
              isActive={activeTab === 'bias'}
              onClick={() => toggleTab('bias')}
              color={bias_audit.risk_level === 'high' ? 'danger' : bias_audit.risk_level === 'medium' ? 'warning' : 'success'}
              badge={bias_audit.flags?.length || 0}
            />
          </div>

          {/* Expandable content */}
          <AnimatePresence mode="wait">
            {activeTab === 'interview' && (
              <ExpandedPanel key="interview">
                <div className="space-y-4">
                  {interview_questions.map((q, i) => (
                    <div key={i} className="flex gap-4">
                      <span className="flex-shrink-0 mt-1 text-sm font-mono text-hm-violet/50">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <div>
                        <p className="text-sm text-hm-text leading-relaxed">{q.question}</p>
                        <div className="flex gap-2 mt-2">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-hm-bg/60 border border-hm-surface-border text-hm-text-muted">
                            {q.focus_area}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-hm-cyan/10 border border-hm-cyan/30 text-hm-cyan">
                            {q.target_skill}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ExpandedPanel>
            )}

            {activeTab === 'bias' && (
              <ExpandedPanel key="bias">
                {/* Risk level badge */}
                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-mono ${biasRiskBg[bias_audit.risk_level || 'low']}`}>
                  {bias_audit.risk_level === 'low' && <CheckCircle2 className="w-4 h-4 text-hm-success" />}
                  {bias_audit.risk_level === 'medium' && <AlertTriangle className="w-4 h-4 text-hm-warning" />}
                  {bias_audit.risk_level === 'high' && <AlertTriangle className="w-4 h-4 text-hm-danger" />}
                  <span className={biasRiskColor[bias_audit.risk_level || 'low']}>
                    {(bias_audit.risk_level || 'low').toUpperCase()} RISK
                  </span>
                  <span className="text-hm-text-muted text-xs">
                    (score: {bias_audit.risk_score || 0}/100)
                  </span>
                </div>

                {/* Flags */}
                {bias_audit.flags?.length > 0 ? (
                  <div className="mt-4 space-y-2">
                    {bias_audit.flags.map((flag, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 text-sm text-hm-text-muted bg-hm-bg/60 rounded p-3 border border-hm-surface-border"
                      >
                        <AlertTriangle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
                          flag.severity === 'high' ? 'text-hm-danger' :
                          flag.severity === 'medium' ? 'text-hm-warning' : 'text-hm-text-muted'
                        }`} />
                        <span>{flag.detail}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-4 text-sm text-hm-text-muted">No bias flags detected.</p>
                )}

                {/* Disclaimer */}
                <p className="mt-4 text-[10px] text-hm-text-muted/60 font-mono leading-relaxed">
                  ⚠️ {bias_audit.disclaimer || 'This is an automated heuristic screening — not a legal or compliance determination.'}
                </p>
              </ExpandedPanel>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

function TabButton({ label, icon, isActive, onClick, color = 'cyan', badge }) {
  const colorMap = {
    cyan: isActive ? 'bg-hm-cyan/10 border-hm-cyan/40 text-hm-cyan' : 'border-hm-surface-border bg-hm-bg/40 text-hm-text-muted hover:border-hm-cyan/30 hover:text-hm-cyan',
    violet: isActive ? 'bg-hm-violet/10 border-hm-violet/40 text-hm-violet' : 'border-hm-surface-border bg-hm-bg/40 text-hm-text-muted hover:border-hm-violet/30 hover:text-hm-violet',
    success: isActive ? 'bg-hm-success/10 border-hm-success/40 text-hm-success' : 'border-hm-surface-border bg-hm-bg/40 text-hm-text-muted hover:border-hm-success/30 hover:text-hm-success',
    warning: isActive ? 'bg-hm-warning/10 border-hm-warning/40 text-hm-warning' : 'border-hm-surface-border bg-hm-bg/40 text-hm-text-muted hover:border-hm-warning/30 hover:text-hm-warning',
    danger: isActive ? 'bg-hm-danger/10 border-hm-danger/40 text-hm-danger' : 'border-hm-surface-border bg-hm-bg/40 text-hm-text-muted hover:border-hm-danger/30 hover:text-hm-danger',
  };

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 px-4 py-1.5 rounded border text-xs font-mono transition-colors duration-200 ${colorMap[color]}`}
    >
      {icon}
      {label}
      {badge > 0 && (
        <span className="ml-1 px-1.5 py-0.5 rounded bg-current/20 text-[10px]">
          {badge}
        </span>
      )}
    </button>
  );
}

function ExpandedPanel({ children }) {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="overflow-hidden"
    >
      <div className="mt-4 pt-4 border-t border-hm-surface-border">
        {children}
      </div>
    </motion.div>
  );
}
