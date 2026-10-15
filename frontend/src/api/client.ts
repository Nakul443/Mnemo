// this file is responsible for defining the API client that will be used to make requests to the backend

import type {
  ChatResponse,
  CreateSessionResponse,
  GraphSnapshot,
  HealthResponse,
  SessionMessagesResponse,
} from "./types";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!res.ok) {
      let detail = "An unexpected error occurred.";
      try {
        const errorJson = await res.json();
        if (errorJson && typeof errorJson.detail === "string") {
          detail = errorJson.detail;
        }
      } catch {
        // Response wasn't JSON
      }
      throw new ApiError(res.status, detail);
    }

    return (await res.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(0, "network");
  }
}

export const api = {
  getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },

  createSession(): Promise<CreateSessionResponse> {
    return request<CreateSessionResponse>("/sessions", {
      method: "POST",
    });
  },

  getMessages(sessionId: string): Promise<SessionMessagesResponse> {
    return request<SessionMessagesResponse>(`/sessions/${sessionId}/messages`);
  },

  sendChat(sessionId: string, message: string): Promise<ChatResponse> {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  },

  getGraph(): Promise<GraphSnapshot> {
    return request<GraphSnapshot>("/graph");
  },
};
