/** Central API base URL — configurable via env var */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// ─── Generic fetch wrapper ────────────────────────────────────

async function getAuthToken() {
  if (typeof window !== "undefined") {
    // @ts-ignore
    return window.Clerk?.session?.getToken();
  }
  return null;
}

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = await getAuthToken();
  const res = await fetch(`${API_BASE}${path}`, {
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
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
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
    const res = await fetch(`${API_BASE}/api/chat/audit`, {
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

    const res = await fetch(`${API_BASE}/api/chat/upload`, {
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
