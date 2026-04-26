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

// ============ Auth ============
export const login = (username: string, password: string) =>
  api.post("/auth/login", { username, password });

export const changePassword = (old_password: string, new_password: string) =>
  api.post("/auth/change-password", { old_password, new_password });

export const getMe = () => api.get("/auth/me");

// ============ Users (Admin) ============
export const listUsers = () => api.get("/users");
export const createUser = (data: object) => api.post("/users", data);
export const updateUser = (id: number, data: object) => api.patch(`/users/${id}`, data);
export const deleteUser = (id: number) => api.delete(`/users/${id}`);
export const resetUserPassword = (id: number, new_password: string) =>
  api.post(`/users/${id}/reset-password`, { new_password });

// ============ Regions ============
export interface RegionDTO {
  id: number;
  code: string;
  name: string;
  full_name: string;
  level: number;
  parent_id: number | null;
  agro_zone: string | null;
}

export const listProvinces = () => api.get<RegionDTO[]>("/regions/provinces");
export const listRegionChildren = (parent_id: number) =>
  api.get<RegionDTO[]>("/regions/children", { params: { parent_id } });
export const searchRegions = (q: string) =>
  api.get<RegionDTO[]>("/regions/search", { params: { q } });
export const getRegion = (id: number) => api.get<RegionDTO>(`/regions/${id}`);

// ============ Crops ============
export interface CropDTO {
  id: number;
  code: string;
  name: string;
  category: string;
  description?: string | null;
}

export interface PhenologyStageDTO {
  stage_name: string;
  description: string | null;
  key_activities: string[];
}

export const getCropTree = () => api.get<Record<string, CropDTO[]>>("/crops/tree");
export const getPopularCrops = () => api.get<CropDTO[]>("/crops/popular");
export const searchCrops = (q: string) =>
  api.get<CropDTO[]>("/crops/search", { params: { q } });
export const getCropPhenology = (crop_id: number, region_id: number) =>
  api.get<{ current_stage: PhenologyStageDTO | null }>(
    `/crops/${crop_id}/phenology`, { params: { region_id } }
  );

// ============ Conversations ============
export interface ConversationDTO {
  id: number;
  title: string;
  region_id: number;
  crop_id: number;
  created_at: string;
  updated_at: string;
}

export interface MessageDTO {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ProposedReminder {
  title: string;
  scheduled_date: string;        // YYYY-MM-DD
  task_description: string;
  operation_steps?: string;
  key_notes?: string;
  region_id?: number | null;
  crop_id?: number | null;
  conversation_id?: number | null;
}

export interface AskResponse {
  conversation_id: number;
  message_id: number;
  answer: string;
  phenology_stage: string | null;
  proposal_ids: number[];
  proposed_reminders: ProposedReminder[];
  reminder_summary: string;
}

export const listConversations = () => api.get<ConversationDTO[]>("/conversations");
export const getConversation = (id: number) =>
  api.get<ConversationDTO & { messages: MessageDTO[] }>(`/conversations/${id}`);
export const createConversation = (region_id: number, crop_id: number, title?: string) =>
  api.post<ConversationDTO>("/conversations", { region_id, crop_id, title });
export const askInConversation = (conversation_id: number, question: string) =>
  api.post<AskResponse>(`/conversations/${conversation_id}/ask`, { question });
export const deleteConversation = (id: number) => api.delete(`/conversations/${id}`);

// ============ Memories ============
export interface MemoryItemDTO {
  id: number;
  key: string;
  value: string;
  confidence: number;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  memory_id: number | null;
  items: MemoryItemDTO[];
}

export interface MemoryProposalDTO {
  id: number;
  memory_id: number;
  action: "add" | "update" | "delete";
  key: string;
  proposed_value: string;
  existing_value: string | null;
  confidence: number;
  reason: string | null;
  created_at: string;
}

export const listMemories = (region_id: number, crop_id: number) =>
  api.get<MemoryListResponse>("/memories", { params: { region_id, crop_id } });
export const createMemoryItem = (
  region_id: number, crop_id: number, key: string, value: string
) => api.post("/memories/items", { region_id, crop_id, key, value });
export const updateMemoryItem = (id: number, value: string) =>
  api.put(`/memories/items/${id}`, { value });
export const deleteMemoryItem = (id: number) => api.delete(`/memories/items/${id}`);

export const listMemoryProposals = (conversation_id?: number) =>
  api.get<MemoryProposalDTO[]>("/memories/proposals", {
    params: conversation_id !== undefined ? { conversation_id } : {},
  });
export const acceptMemoryProposal = (id: number) =>
  api.post(`/memories/proposals/${id}/accept`);
export const rejectMemoryProposal = (id: number) =>
  api.post(`/memories/proposals/${id}/reject`);

// ============ Reminders ============
export interface ReminderDTO {
  id: number;
  conversation_id: number | null;
  region_id: number | null;
  crop_id: number | null;
  region_name: string;
  crop_name: string;
  scheduled_date: string;        // YYYY-MM-DD
  title: string;
  task_description: string;
  operation_steps: string;
  key_notes: string;
  is_done: boolean;
  created_at: string;
}

export const listReminders = (year?: number, month?: number) =>
  api.get<ReminderDTO[]>("/reminders", { params: { year, month } });

export const batchCreateReminders = (items: ProposedReminder[]) =>
  api.post<number[]>("/reminders/batch", { items });

export const toggleReminderDone = (id: number) =>
  api.patch(`/reminders/${id}/done`);

export const deleteReminder = (id: number) =>
  api.delete(`/reminders/${id}`);
