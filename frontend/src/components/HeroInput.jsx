import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, X, Sparkles, AlertCircle } from 'lucide-react';

/**
 * Hero input section: JD textarea + drag-and-drop resume upload + submit button.
 */
export default function HeroInput({ onSubmit, isLoading }) {
  const [jobDescription, setJobDescription] = useState('');
  const [resumeTexts, setResumeTexts] = useState([]);
  const [resumeNames, setResumeNames] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    processFiles(files);
    e.target.value = '';
  };

  const processFiles = async (files) => {
    const textFiles = files.filter(
      (f) => f.type === 'text/plain' || f.name.endsWith('.txt') || f.name.endsWith('.pdf') || f.name.endsWith('.doc') || f.name.endsWith('.docx')
    );
    const otherFiles = files.filter(
      (f) => !f.type.startsWith('text/') && !f.name.endsWith('.txt') && !f.name.endsWith('.pdf') && !f.name.endsWith('.doc') && !f.name.endsWith('.docx')
    );

    if (otherFiles.length > 0) {
      setError('Only .txt, .pdf, and .doc/docx files are supported.');
    } else {
      setError('');
    }

    for (const file of textFiles) {
      const text = await file.text();
      if (text.trim()) {
        setResumeTexts((prev) => [...prev, text.trim()]);
        setResumeNames((prev) => [...prev, file.name]);
      }
    }

    // If non-text files, treat filenames as short resume text (demo convenience)
    for (const file of otherFiles) {
      setResumeTexts((prev) => [...prev, `Resume: ${file.name}`]);
      setResumeNames((prev) => [...prev, file.name]);
    }
  };

  const removeResume = (index) => {
    setResumeTexts((prev) => prev.filter((_, i) => i !== index));
    setResumeNames((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    if (!jobDescription.trim()) {
      setError('Please enter a job description.');
      return;
    }
    if (resumeTexts.length < 2 || resumeTexts.length > 20) {
      setError('Please upload between 2 and 20 resumes.');
      return;
    }
    setError('');
    onSubmit(jobDescription, resumeTexts);
  };

  const handlePasteSampleJD = () => {
    setJobDescription(`Senior Full-Stack Engineer — Series B SaaS Startup

We're looking for a Senior Full-Stack Engineer to join our core platform team. You'll own the design and implementation of critical user-facing features and backend APIs powering our analytics dashboard.

Required Skills:
- Python (FastAPI or Django) — 4+ years production experience
- React + TypeScript — component architecture, state management
- PostgreSQL — schema design, query optimization
- Docker & Kubernetes — containerized deployments
- AWS or GCP — cloud infrastructure, CI/CD pipelines

Nice to Have:
- Machine learning / data pipeline experience
- GraphQL API design
- Terraform / infrastructure-as-code
- Experience leading small teams (2-4 engineers)

Experience: 5-8 years in software engineering
Role: Full-stack with backend emphasis
Location: Remote (US/India timezones preferred)`);
  };

  const handleAddSampleResumes = () => {
    const sampleResumes = [
      `Arjun Mehta
Senior Software Engineer | 6 years experience

Skills: Python, FastAPI, Docker, PostgreSQL, AWS, Machine Learning, React, TypeScript
Education: M.Tech Computer Science, IIT Bombay

Summary: Full-stack engineer with 6 years building scalable Python microservices and ML pipelines. Led a team of 4 at a Series-B startup. Designed and deployed a real-time analytics API serving 2M daily requests. Strong experience with Docker/K8s deployments on AWS.`,

      `Sarah Chen
Staff Software Engineer | 8 years experience

Skills: Python, Django, React, TypeScript, Kubernetes, Terraform, GraphQL
Education: MS Computer Science, Stanford University

Summary: Staff engineer with deep expertise in distributed systems and infrastructure. Built real-time data platforms serving 10M+ users at a FAANG company. Led migration from monolith to microservices architecture. Expert in Terraform IaC and Kubernetes orchestration.`,

      `Priya Sharma
Data Engineer | 4 years experience

Skills: Python, Data Engineering, Apache Spark, Airflow, SQL, GCP, Kafka
Education: B.Tech Computer Science, NIT Trichy

Summary: Data engineer specializing in batch and streaming pipelines. Reduced ETL latency by 60% at previous role using Spark optimizations. Built real-time event processing with Kafka. Strong SQL skills with BigQuery and PostgreSQL.`,

      `James Wilson
Full-Stack Developer | 5 years experience

Skills: JavaScript, React, Node.js, TypeScript, MongoDB, Redis, Docker
Education: BS Computer Science, UC Berkeley

Summary: Frontend-focused full-stack developer with deep React expertise. Built shared component libraries used across 3 product teams. Experience with Node.js microservices and MongoDB. Comfortable with Docker but limited cloud infrastructure experience.`,

      `Maria Rodriguez
ML Engineer | 7 years experience

Skills: Python, Machine Learning, Deep Learning, PyTorch, NLP, FastAPI, Docker
Education: PhD Machine Learning, MIT

Summary: ML engineer with publications in NeurIPS and ICML. Deployed production NLP models serving 1M+ daily predictions. Built end-to-end ML pipelines with FastAPI serving layers. Strong Python skills but limited frontend experience.`,
    ];

    const names = [
      'arjun_mehta_resume.txt',
      'sarah_chen_resume.txt',
      'priya_sharma_resume.txt',
      'james_wilson_resume.txt',
      'maria_rodriguez_resume.txt',
    ];

    setResumeTexts(sampleResumes);
    setResumeNames(names);
  };

  return (
    <section className="w-full max-w-2xl mx-auto px-4">
      {/* Header text (small brand mark) */}
      <div className="absolute top-8 left-1/2 -translate-x-1/2 text-center pointer-events-none">
        <h1 className="text-hm-text text-xl tracking-[0.2em] font-mono opacity-80 uppercase">
          HireMind
        </h1>
      </div>

      <div className="glass-panel p-6 shadow-2xl shadow-hm-violet/5">
        {/* Job Description */}
        <div className="mb-6 relative">
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste job description..."
            className="w-full h-32 bg-transparent border-0 border-b border-hm-surface-border p-4 text-hm-text font-mono text-sm leading-relaxed resize-none focus:outline-none focus:border-hm-cyan/50 transition-colors custom-scrollbar placeholder:text-hm-text-muted"
            disabled={isLoading}
          />
          <button
            onClick={handlePasteSampleJD}
            className="absolute top-4 right-4 text-[10px] font-mono text-hm-violet hover:text-hm-cyan transition-colors px-2 py-1 rounded bg-hm-surface-border/20"
          >
            SAMPLE JD
          </button>
        </div>

        {/* Resume Upload */}
        <div className="mb-6">
          <div
            className={`drop-zone ${isDragOver ? 'drag-over' : ''} py-6`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.pdf,.doc,.docx"
              onChange={handleFileSelect}
              className="hidden"
            />
            <div className="flex items-center justify-center gap-3">
              <Upload className={`w-5 h-5 transition-colors ${isDragOver ? 'text-hm-cyan' : 'text-hm-text-muted'}`} />
              <p className="text-hm-text-muted font-mono text-sm">
                Drop resumes here <span className="opacity-50 text-xs">(2-20 resumes, txt, pdf, docx)</span>
              </p>
            </div>
          </div>
          
          <div className="flex justify-end mt-2">
            <button
              onClick={handleAddSampleResumes}
              className="text-[10px] font-mono text-hm-violet hover:text-hm-cyan transition-colors px-2 py-1 rounded bg-hm-surface-border/20"
            >
              LOAD 5 SAMPLE RESUMES
            </button>
          </div>

          {/* Uploaded files list */}
          <AnimatePresence>
            {resumeNames.length > 0 && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-4 space-y-2 overflow-hidden"
              >
                {resumeNames.map((name, index) => (
                  <motion.div
                    key={`${name}-${index}`}
                    initial={{ x: -10, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 10, opacity: 0 }}
                    className="flex items-center justify-between bg-hm-bg/50 rounded px-3 py-1.5 border border-hm-surface-border"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="w-3 h-3 text-hm-violet" />
                      <span className="text-xs font-mono text-hm-text-muted">{name}</span>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); removeResume(index); }}
                      className="text-hm-text-muted hover:text-hm-danger transition-colors p-1"
                      disabled={isLoading}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Error display */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="flex items-center gap-2 text-hm-danger text-xs font-mono mb-4 px-1"
            >
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={isLoading || resumeTexts.length < 2 || resumeTexts.length > 20}
          className={`btn-glow w-full flex items-center justify-center gap-2 ${
            resumeTexts.length > 0 && (resumeTexts.length < 2 || resumeTexts.length > 20) ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isLoading ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeDasharray="60" strokeDashoffset="20" />
              </svg>
              ANALYZING...
            </>
          ) : (
            'ANALYZE CANDIDATES'
          )}
        </button>
      </div>
    </section>
  );
}
