import { getSession } from "next-auth/react";

/** Central API base URL — configurable via env var */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// ─── Generic fetch wrapper ────────────────────────────────────

async function getAuthToken() {
  if (typeof window !== "undefined") {
    const session = await getSession();
    if (!session) {
      console.warn("[API] No active session found via getSession()");
      return null;
    }
    
    console.debug("[API] Session found:", {
      user: session.user ? "present" : "absent",
      expires: session.expires,
      hasAccessToken: !!(session as any).accessToken || !!(session.user as any)?.accessToken
    });

    // Check both root and user object (for robustness)
    const token = (session as any).accessToken || (session.user as any)?.accessToken;
    
    if (!token) {
      console.warn("[API] Session found, but accessToken is MISSING. Session object keys:", Object.keys(session), "User keys:", session.user ? Object.keys(session.user) : "N/A");
    }
    
    return token || null;
  }
  return null;
}

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = await getAuthToken();
  if (token) {
    console.debug(`[API] Fetching ${path} with token present`);
  } else {
    console.warn(`[API] Fetching ${path} WITHOUT token!`);
  }
  
  // Ensure path starts with / if not absolute
  const targetPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${API_BASE}${targetPath}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Types (mirroring backend schemas) ───────────────────────

export interface ApiConversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  messages: ApiMessage[];
  contractType?: string;
  userType?: string;
  verdict?: string;
  isPinned: boolean;
}

export interface ApiMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  attachment?: {
    id: string;
    name: string;
    size: number;
    type: string;
  };
}

// ─── Conversations ────────────────────────────────────────────

export const conversationsApi = {
  list(): Promise<ApiConversation[]> {
    return apiFetch("/api/conversations");
  },

  create(data: {
    title?: string;
    contract_type?: string;
    user_type?: string;
  }): Promise<ApiConversation> {
    return apiFetch("/api/conversations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  get(id: string): Promise<ApiConversation> {
    return apiFetch(`/api/conversations/${id}`);
  },

  update(
    id: string,
    data: { title?: string; is_pinned?: boolean }
  ): Promise<ApiConversation> {
    return apiFetch(`/api/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  delete(id: string): Promise<{ success: boolean }> {
    return apiFetch(`/api/conversations/${id}`, { method: "DELETE" });
  },
};

// ─── Chat ─────────────────────────────────────────────────────

export const chatApi = {
  /** Non-streaming send */
  send(data: {
    message: string;
    conversation_id?: string;
    user_type?: string;
    contract_type?: string;
  }): Promise<{ message: ApiMessage; conversation_id: string }> {
    return apiFetch("/api/chat", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /**
   * Streaming send — returns a ReadableStream of SSE events.
   * Yields parsed JSON objects from each `data:` line.
   */
  async *stream(data: {
    message: string;
    conversation_id?: string;
    user_type?: string;
    contract_type?: string;
  }, signal?: AbortSignal): AsyncGenerator<Record<string, unknown>> {
    const token = await getAuthToken();
    console.debug(`[API] Streaming with token: ${token ? 'present' : 'MISSING'}`);
    const url = `${API_BASE}/api/chat/stream`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
      signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Stream error ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6)) as Record<string, unknown>;
          } catch {
            // ignore malformed lines
          }
        }
      }
    }
  },

  /**
   * Audit pipeline — yields SSE events with step updates + content chunks.
   */
  async *audit(data: {
    message: string;
    conversation_id?: string;
    user_type?: string;
    contract_type?: string;
  }, signal?: AbortSignal): AsyncGenerator<Record<string, unknown>> {
    const token = await getAuthToken();
    console.debug(`[API] Auditing with token: ${token ? 'present' : 'MISSING'}`);
    const url = `${API_BASE}/api/chat/audit`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
      signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Audit stream error ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6)) as Record<string, unknown>;
          } catch {
            // ignore malformed lines
          }
        }
      }
    }
  },

  /** Upload a document file */
  async upload(
    file: File,
    conversationId: string
  ): Promise<{ id: string; name: string; size: number; type: string; conversation_id: string }> {
    const form = new FormData();
    form.append("file", file);
    form.append("conversation_id", conversationId);
    
    const token = await getAuthToken();
    console.debug(`[API] Uploading with token: ${token ? 'present' : 'MISSING'}`);
    const url = `${API_BASE}/api/chat/upload`;

    const res = await fetch(url, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: form,
      // No Content-Type header — browser sets it with boundary for multipart
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? `Upload error ${res.status}`);
    }

    return res.json();
  },
};
