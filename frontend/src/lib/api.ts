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
  },
};
