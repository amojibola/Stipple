const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    credentials: "include",
  });

  if (!res.ok) {
    let code = "unknown_error";
    let message = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      code = body.error ?? code;
      message = body.message ?? message;
    } catch {
      // non-JSON error body — use defaults
    }
    throw new ApiError(res.status, code, message);
  }

  return res.json() as Promise<T>;
}

async function upload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
    credentials: "include",
    // No Content-Type header — browser sets multipart boundary automatically
  });

  if (!res.ok) {
    let code = "unknown_error";
    let message = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      code = body.error ?? code;
      message = body.message ?? message;
    } catch {
      // non-JSON error body — use defaults
    }
    throw new ApiError(res.status, code, message);
  }

  return res.json() as Promise<T>;
}

export interface UploadedFile {
  id: string;
  mime_type: string;
  file_size_bytes: number;
  width_px: number;
  height_px: number;
  megapixels: string;
  uploaded_at: string;
}

export interface StippleParams {
  dot_size: number;
  density: number;
  black_point: number;
  highlights: number;
  shadow_depth: number;
}

export interface JobCreateResponse {
  job_id: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
}

export interface Project {
  id: string;
  name: string;
  source_file_id: string | null;
  parameters: StippleParams | Record<string, unknown>;
  status: "draft" | "processing" | "ready" | "failed";
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface ProjectCreateRequest {
  name: string;
  source_file_id?: string;
  parameters?: StippleParams;
}

export interface ProjectUpdateRequest {
  name?: string;
  parameters?: StippleParams;
}

export interface UserProfile {
  id: string;
  email: string;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QuotaResponse {
  renders_today: number;
  renders_this_month: number;
  daily_limit: number;
  monthly_limit: number;
  day_reset_at: string;
  month_reset_at: string;
  updated_at: string;
}

export const api = {
  auth: {
    register: (email: string, password: string) =>
      request<{ message: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    verify: (token: string) =>
      request<{ message: string }>("/auth/verify", {
        method: "POST",
        body: JSON.stringify({ token }),
      }),

    login: (email: string, password: string) =>
      request<{ message: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    refresh: () =>
      request<{ message: string }>("/auth/refresh", { method: "POST" }),

    logout: () =>
      request<{ message: string }>("/auth/logout", { method: "POST" }),

    forgotPassword: (email: string) =>
      request<{ message: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),

    resetPassword: (token: string, password: string) =>
      request<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      }),
  },

  images: {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return upload<UploadedFile>("/images/upload", formData);
    },

    delete: (fileId: string) =>
      fetch(`${API_BASE}/images/${fileId}`, {
        method: "DELETE",
        credentials: "include",
      }).then((res) => {
        if (!res.ok) throw new ApiError(res.status, "delete_failed", "Delete failed");
      }),

    getUrl: (fileId: string) => `${API_BASE}/images/${fileId}`,

    preview: async (fileId: string, params: StippleParams): Promise<Blob> => {
      const res = await fetch(`${API_BASE}/images/${fileId}/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(params),
      });
      if (!res.ok) {
        let code = "preview_failed";
        let message = "Preview generation failed";
        try {
          const body = await res.json();
          code = body.error ?? code;
          message = body.message ?? message;
        } catch { /* ignore */ }
        throw new ApiError(res.status, code, message);
      }
      return res.blob();
    },
  },

  jobs: {
    create: (sourceFileId: string, parameters: StippleParams) =>
      request<JobCreateResponse>("/jobs", {
        method: "POST",
        body: JSON.stringify({ source_file_id: sourceFileId, parameters }),
      }),

    getStatus: (jobId: string) =>
      request<JobStatusResponse>(`/jobs/${jobId}/status`),

    downloadResult: async (jobId: string): Promise<void> => {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/result`, {
        credentials: "include",
      });
      if (!res.ok) throw new ApiError(res.status, "download_failed", "Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `stipple_${jobId}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  },

  projects: {
    list: (page = 1, limit = 20) =>
      request<ProjectListResponse>(`/projects?page=${page}&limit=${limit}`),

    get: (projectId: string) =>
      request<Project>(`/projects/${projectId}`),

    create: (body: ProjectCreateRequest) =>
      request<Project>("/projects", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    update: (projectId: string, body: ProjectUpdateRequest) =>
      request<Project>(`/projects/${projectId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    delete: (projectId: string) =>
      fetch(`${API_BASE}/projects/${projectId}`, {
        method: "DELETE",
        credentials: "include",
      }).then((res) => {
        if (!res.ok) throw new ApiError(res.status, "delete_failed", "Delete failed");
      }),
  },

  users: {
    me: () => request<UserProfile>("/users/me"),

    updateMe: (body: { email?: string }) =>
      request<UserProfile>("/users/me", {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteMe: () =>
      fetch(`${API_BASE}/users/me`, {
        method: "DELETE",
        credentials: "include",
      }).then((res) => {
        if (!res.ok) throw new ApiError(res.status, "delete_failed", "Delete failed");
      }),

    quota: () => request<QuotaResponse>("/users/me/quota"),
  },
};
