import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Pull the FastAPI `detail` message out of an axios/fetch error, if there is one
export const getErrorMessage = (error, fallback = 'Something went wrong') => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return error?.message || fallback;
};

export const chatApi = {
  sendMessage: (query, sessionId = null) =>
    api.post('/api/chat/', { query, session_id: sessionId }),

  streamMessage: (query, sessionId = null, onToken, onSources, onDone, onError) => {
    const url = `${API_BASE_URL}/api/chat/stream`;

    const fetchStream = async () => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query, session_id: sessionId }),
        });

        if (!response.ok) {
          let detail = `Request failed (${response.status})`;
          try {
            const body = await response.json();
            if (typeof body.detail === 'string') detail = body.detail;
          } catch {
            // non-JSON error body — keep the generic message
          }
          throw new Error(detail);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let fullAnswer = '';
        let sources = [];
        let finished = false;
        // A network chunk can end in the middle of an SSE event, so keep the
        // unfinished tail here and only parse complete events
        let buffer = '';

        const handleEvent = (event) => {
          if (!event.startsWith('data: ')) return;
          try {
            const data = JSON.parse(event.slice(6));
            if (data.type === 'token') {
              fullAnswer += data.content;
              onToken(data.content);
            }
            if (data.type === 'sources') {
              sources = data.sources;
              onSources(data.sources);
            }
            if (data.type === 'done') {
              finished = true;
              onDone(data.session_id, fullAnswer, sources);
            }
          } catch (e) {
            console.error("Error parsing stream data", e);
          }
        };

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          // stream: true keeps multi-byte characters intact across chunk boundaries
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop();
          events.forEach(handleEvent);
        }

        buffer += decoder.decode();
        if (buffer.trim()) handleEvent(buffer.trim());

        if (!finished) throw new Error('The response stream ended unexpectedly');
      } catch (error) {
        if (onError) onError(error);
      }
    };

    fetchStream();
  }
};

export const documentApi = {
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  list: () => api.get('/api/documents/'),
  reindex: (id) => api.post(`/api/documents/${id}/reindex`),
  delete: (id) => api.delete(`/api/documents/${id}`),
};

export const historyApi = {
  listSessions: () => api.get('/api/history/sessions'),
  getSession: (id) => api.get(`/api/history/sessions/${id}`),
  deleteSession: (id) => api.delete(`/api/history/sessions/${id}`),
  clearAll: () => api.delete('/api/history/sessions'),
};

export default api;
