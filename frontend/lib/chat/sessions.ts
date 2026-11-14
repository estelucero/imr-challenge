export type ChatMessageBpmn = {
    id: string;
    name: string;
    xml: string;
};

export type ChatMessage = {
    id: string;
    role: "user" | "assistant";
    text: string;
    bpmn?: ChatMessageBpmn;
};

export type ChatSession = {
    id: string;
    title: string;
    createdAt: number;
    updatedAt: number;
    messages: ChatMessage[];
};

const SESSIONS_KEY = "imr-chat-sessions";
const ACTIVE_KEY = "imr-chat-active-session";

function isChatMessage(value: unknown): value is ChatMessage {
    if (typeof value !== "object" || value === null) return false;
    const item = value as Record<string, unknown>;
    return (
        typeof item.id === "string" &&
        (item.role === "user" || item.role === "assistant") &&
        typeof item.text === "string"
    );
}

function isChatSession(value: unknown): value is ChatSession {
    if (typeof value !== "object" || value === null) return false;
    const item = value as Record<string, unknown>;
    return (
        typeof item.id === "string" &&
        typeof item.title === "string" &&
        typeof item.createdAt === "number" &&
        typeof item.updatedAt === "number" &&
        Array.isArray(item.messages) &&
        item.messages.every(isChatMessage)
    );
}

function readJson(key: string): unknown {
    if (typeof window === "undefined" || !window.localStorage) return null;
    try {
        const raw = window.localStorage.getItem(key);
        return raw ? JSON.parse(raw) : null;
    } catch (error) {
        console.error(`No se pudo leer ${key}`, error);
        return null;
    }
}

function writeJson(key: string, value: unknown): boolean {
    if (typeof window === "undefined" || !window.localStorage) return false;
    try {
        window.localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (error) {
        console.error(`No se pudo escribir ${key}`, error);
        return false;
    }
}

/** Lista las sesiones guardadas, del chat más reciente al más viejo. */
export function listSessions(): ChatSession[] {
    const parsed = readJson(SESSIONS_KEY);
    if (!Array.isArray(parsed)) return [];
    return parsed
        .filter(isChatSession)
        .sort((a, b) => b.updatedAt - a.updatedAt);
}

export function writeSessions(sessions: ChatSession[]): boolean {
    return writeJson(SESSIONS_KEY, sessions);
}

export function readActiveSessionId(): string | null {
    const parsed = readJson(ACTIVE_KEY);
    return typeof parsed === "string" ? parsed : null;
}

export function writeActiveSessionId(id: string | null): void {
    writeJson(ACTIVE_KEY, id);
}
