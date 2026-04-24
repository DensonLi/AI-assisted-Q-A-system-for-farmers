import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const { data } = await axios.post("/api/v1/auth/refresh", {
            refresh_token: refreshToken,
          });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
        }
      } else {
        localStorage.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const login = (username: string, password: string) =>
  api.post("/auth/login", { username, password });

export const changePassword = (old_password: string, new_password: string) =>
  api.post("/auth/change-password", { old_password, new_password });

export const getMe = () => api.get("/auth/me");

// Users (Admin)
export const listUsers = () => api.get("/users");
export const createUser = (data: object) => api.post("/users", data);
export const updateUser = (id: number, data: object) => api.patch(`/users/${id}`, data);
export const deleteUser = (id: number) => api.delete(`/users/${id}`);
export const resetUserPassword = (id: number, new_password: string) =>
  api.post(`/users/${id}/reset-password`, { new_password });

// Conversations
export const listConversations = () => api.get("/conversations");
export const getConversation = (id: number) => api.get(`/conversations/${id}`);
export const askQuestion = (question: string, conversation_id?: number) =>
  api.post("/conversations/ask", { question, conversation_id });
export const deleteConversation = (id: number) => api.delete(`/conversations/${id}`);
