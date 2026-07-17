/**
 * API client for the HireMind backend.
 * Supports both synchronous POST /rank and SSE streaming via /rank/stream.
 */

const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

/**
 * Rank candidates (synchronous).
 * @param {string} jobDescription 
 * @param {string[]} resumes 
 * @returns {Promise<object>}
 */
export async function rankCandidates(jobDescription, resumes) {
  const response = await fetch(`${BASE_URL}/rank`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_description: jobDescription,
      resumes: resumes,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Stream ranking pipeline with real-time status updates via SSE.
 * @param {string} jobDescription 
 * @param {string[]} resumes 
 * @param {function} onStatus - Called with { agent, status } on each pipeline stage
 * @param {function} onResult - Called with the final result object
 * @param {function} onError  - Called on error
 */
export function streamRanking(jobDescription, resumes, onStatus, onResult, onError) {
  // Use fetch + ReadableStream for SSE POST requests
  // (EventSource only supports GET)
  const controller = new AbortController();

  fetch(`${BASE_URL}/rank/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_description: jobDescription,
      resumes: resumes,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Stream error' }));
        onError(new Error(err.detail || `HTTP ${response.status}`));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            const data = line.slice(5).trim();
            if (!data) continue;

            try {
              const parsed = JSON.parse(data);
              if (currentEvent === 'status') {
                onStatus(parsed);
              } else if (currentEvent === 'result') {
                onResult(parsed);
              }
            } catch {
              // Ignore parse errors for partial chunks
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err);
      }
    });

  return () => controller.abort();
}

/**
 * Health check.
 * @returns {Promise<object>}
 */
export async function healthCheck() {
  const response = await fetch(`${BASE_URL}/health`);
  return response.json();
}
