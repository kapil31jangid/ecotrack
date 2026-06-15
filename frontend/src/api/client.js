import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 30000,
});

// Request interceptor injecting session identifiers
api.interceptors.request.use(
  (config) => {
    const sessionId = localStorage.getItem("ecotrack_session_id");
    if (sessionId) {
      config.headers["X-Session-ID"] = sessionId;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to normalize error signatures
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = "An unexpected error occurred.";
    if (error.response) {
      // Check for structural API error objects
      if (typeof error.response.data === "object") {
        message = error.response.data.error || error.response.data.detail || message;
        if (Array.isArray(message)) {
          // Normalize Pydantic validation errors
          message = message.map(err => `${err.loc.join(".")}: ${err.msg}`).join("; ");
        }
      } else {
        message = `Server error: ${error.response.statusText}`;
      }
    } else if (error.request) {
      message = "Network error: No response received from server. Please verify your connection.";
    } else {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);

export const calculateFootprint = (data) => api.post("/calculate", data).then(r => r.data);
export const sendChat = (data) => api.post("/chat", data).then(r => r.data);
export const getHistory = (sessionId) => api.get(`/history/${sessionId}`).then(r => r.data);
