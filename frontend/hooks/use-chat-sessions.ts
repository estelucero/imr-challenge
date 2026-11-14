"use client";

import * as React from "react";

import {
    listSessions,
    readActiveSessionId,
    writeActiveSessionId,
    writeSessions,
    type ChatMessage,
    type ChatSession,
} from "@/lib/chat/sessions";

function truncate(text: string, max = 40) {
    return text.length > max ? `${text.slice(0, max).trimEnd()}…` : text;
}

function getDate(): string {
    const ahora: Date = new Date();

    // Formato para Argentina/Latinoamérica (DD/MM/YYYY, HH:mm:ss)
    const fechaFormateada: string = ahora.toLocaleString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    });
    return fechaFormateada;
}

export function useChatSessions() {
    const [sessions, setSessions] = React.useState<ChatSession[]>([]);
    const [activeId, setActiveId] = React.useState<string | null>(null);
    const [hydrated, setHydrated] = React.useState(false);

    // Hidratación desde localStorage, en un timeout para que el setState
    // no sea síncrono dentro del effect (regla react-hooks/set-state-in-effect).
    React.useEffect(() => {
        const timer = window.setTimeout(() => {
            const loaded = listSessions();
            const storedActive = readActiveSessionId();
            const active = loaded.some((session) => session.id === storedActive)
                ? storedActive
                : (loaded[0]?.id ?? null);

            setSessions(loaded);
            setActiveId(active);
            setHydrated(true);
        }, 0);

        return () => window.clearTimeout(timer);
    }, []);

    // Estado siempre fresco para los callbacks: el setTimeout del mock del
    // chat se dispara mucho después del render que lo creó, y leer el
    // estado del closure le daba valores viejos (creaba una segunda sesión
    // y pisaba el storage, "borrando" el mensaje del usuario).
    const stateRef = React.useRef({ sessions, activeId });

    React.useEffect(() => {
        stateRef.current = { sessions, activeId };
    });

    const activeSession = sessions.find((s) => s.id === activeId) ?? null;

    /** Limpia la vista; la sesión nueva se crea con el primer mensaje. */
    function newChat() {
        stateRef.current = { ...stateRef.current, activeId: null };
        setActiveId(null);
        writeActiveSessionId(null);
    }

    function selectSession(id: string) {
        stateRef.current = { ...stateRef.current, activeId: id };
        setActiveId(id);
        writeActiveSessionId(id);
    }

    function deleteSession(id: string) {
        const { sessions, activeId } = stateRef.current;

        const rest = sessions.filter((session) => session.id !== id);
        stateRef.current = {
            sessions: rest,
            activeId: id === activeId ? null : activeId,
        };
        setSessions(rest);
        writeSessions(rest);

        if (id === activeId) {
            setActiveId(null);
            writeActiveSessionId(null);
        }
    }

    function addMessage(message: ChatMessage) {
        const { sessions, activeId } = stateRef.current;

        if (!activeId) {
            // Primer mensaje de un chat nuevo: se crea la sesión al vuelo.
            const session: ChatSession = {
                id: crypto.randomUUID(),
                title:
                    message.role === "user"
                        ? truncate(message.text)
                        : getDate(),
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messages: [message],
            };

            const next = [session, ...sessions];
            stateRef.current = { sessions: next, activeId: session.id };
            setSessions(next);
            setActiveId(session.id);
            writeActiveSessionId(session.id);
            writeSessions(next);
            return;
        }

        const next = sessions.map((session) =>
            session.id === activeId
                ? {
                      ...session,
                      // El título se fija con el primer mensaje del usuario.
                      title:
                          message.role === "user" &&
                          !session.messages.some((m) => m.role === "user")
                              ? truncate(message.text)
                              : session.title,
                      updatedAt: Date.now(),
                      messages: [...session.messages, message],
                  }
                : session,
        );
        stateRef.current = { sessions: next, activeId };
        setSessions(next);
        writeSessions(next);
    }

    function updateMessageBpmn(messageId: string, xml: string) {
        const { sessions, activeId } = stateRef.current;
        if (!activeId) return;

        const next = sessions.map((session) =>
            session.id === activeId
                ? {
                      ...session,
                      messages: session.messages.map((message) =>
                          message.id === messageId && message.bpmn
                              ? {
                                    ...message,
                                    bpmn: { ...message.bpmn, xml },
                                }
                              : message,
                      ),
                  }
                : session,
        );
        stateRef.current = { sessions: next, activeId };
        setSessions(next);
        writeSessions(next);
    }

    return {
        sessions,
        activeId,
        activeSession,
        hydrated,
        newChat,
        selectSession,
        deleteSession,
        addMessage,
        updateMessageBpmn,
    };
}
