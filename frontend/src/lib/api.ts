import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import Cookies from "js-cookie";
import type {
  TokenResponse, User, Case, CaseCreate, CaseListResponse,
  Wallet, GraphResponse, RiskAnalysis, VaspAttribution,
  Report, ReportFormat, SystemHealth, Transaction,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const createClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: `${API_URL}/api/v1`,
    timeout: 30000,
    headers: { "Content-Type": "application/json" },
  });

  // Attach token to every request
  client.interceptors.request.use((config) => {
    const token = Cookies.get("tracex_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Handle 401 globally
  client.interceptors.response.use(
    (r) => r,
    (err) => {
      if (err.response?.status === 401) {
        Cookies.remove("tracex_token");
        if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
          window.location.href = "/login";
        }
      }
      return Promise.reject(err);
    }
  );

  return client;
};

const api = createClient();

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: async (username: string, password: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>("/auth/login", { username, password });
    Cookies.set("tracex_token", data.access_token, { expires: 1, sameSite: "strict" });
    return data;
  },
  logout: () => {
    Cookies.remove("tracex_token");
  },
  me: async (): Promise<User> => {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },
  register: async (payload: {
    username: string; email: string; password: string; full_name: string; role?: string;
  }): Promise<User> => {
    const { data } = await api.post<User>("/auth/register", payload);
    return data;
  },
};

// ── Cases ─────────────────────────────────────────────────────────────────────
export const casesApi = {
  list: async (params?: { status?: string; page?: number; page_size?: number }): Promise<CaseListResponse> => {
    const { data } = await api.get<CaseListResponse>("/cases", { params });
    return data;
  },
  create: async (payload: CaseCreate): Promise<Case> => {
    const { data } = await api.post<Case>("/cases", payload);
    return data;
  },
  get: async (id: string): Promise<Case> => {
    const { data } = await api.get<Case>(`/cases/${id}`);
    return data;
  },
  update: async (id: string, payload: Partial<CaseCreate & { status: string }>): Promise<Case> => {
    const { data } = await api.patch<Case>(`/cases/${id}`, payload);
    return data;
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/cases/${id}`);
  },
};

// ── Wallets ───────────────────────────────────────────────────────────────────
export const walletsApi = {
  list: async (caseId: string): Promise<Wallet[]> => {
    const { data } = await api.get<Wallet[]>(`/cases/${caseId}/wallets`);
    return data;
  },
  add: async (caseId: string, payload: { address: string; chain?: string; wallet_type?: string; label?: string }): Promise<Wallet> => {
    const { data } = await api.post<Wallet>(`/cases/${caseId}/wallets`, payload);
    return data;
  },
  getTransactions: async (caseId: string, address: string, page = 1): Promise<Transaction[]> => {
    const { data } = await api.get<Transaction[]>(`/cases/${caseId}/wallets/${address}/transactions`, { params: { page } });
    return data;
  },
};

// ── Graph ─────────────────────────────────────────────────────────────────────
export const graphApi = {
  build: async (caseId: string, walletAddress: string, maxHops = 4): Promise<GraphResponse> => {
    const { data } = await api.post<GraphResponse>(
      `/cases/${caseId}/graph/${walletAddress}`,
      null,
      { params: { max_hops: maxHops } }
    );
    return data;
  },
  get: async (caseId: string, walletAddress: string, maxHops = 4): Promise<GraphResponse> => {
    const { data } = await api.get<GraphResponse>(
      `/cases/${caseId}/graph/${walletAddress}`,
      { params: { max_hops: maxHops } }
    );
    return data;
  },
};

// ── Risk ──────────────────────────────────────────────────────────────────────
export const riskApi = {
  analyze: async (caseId: string, walletAddress: string): Promise<RiskAnalysis> => {
    const { data } = await api.post<RiskAnalysis>(`/cases/${caseId}/risk/${walletAddress}`);
    return data;
  },
  get: async (caseId: string, walletAddress: string): Promise<RiskAnalysis> => {
    const { data } = await api.get<RiskAnalysis>(`/cases/${caseId}/risk/${walletAddress}`);
    return data;
  },
};

// ── VASP ──────────────────────────────────────────────────────────────────────
export const vaspApi = {
  attribute: async (caseId: string, walletAddress: string): Promise<VaspAttribution> => {
    const { data } = await api.post<VaspAttribution>(`/cases/${caseId}/vasp/${walletAddress}`);
    return data;
  },
  get: async (caseId: string, walletAddress: string): Promise<VaspAttribution> => {
    const { data } = await api.get<VaspAttribution>(`/cases/${caseId}/vasp/${walletAddress}`);
    return data;
  },
};

// ── Reports ───────────────────────────────────────────────────────────────────
export const reportsApi = {
  generate: async (caseId: string, format: ReportFormat): Promise<Report> => {
    const { data } = await api.post<Report>(`/cases/${caseId}/reports`, { format });
    return data;
  },
  list: async (caseId: string): Promise<Report[]> => {
    const { data } = await api.get<Report[]>(`/cases/${caseId}/reports`);
    return data;
  },
  downloadUrl: (caseId: string, reportId: string) =>
    `${API_URL}/api/v1/cases/${caseId}/reports/${reportId}/download?token=${Cookies.get("tracex_token")}`,
};

// ── Health ────────────────────────────────────────────────────────────────────
export const healthApi = {
  get: async (): Promise<SystemHealth> => {
    const { data } = await axios.get<SystemHealth>(`${API_URL}/health`);
    return data;
  },
};

export default api;
