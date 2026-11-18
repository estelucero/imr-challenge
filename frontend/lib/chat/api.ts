const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function sendChat(sessionId: string, message: string) {
    const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: "openrouter", model: "deepseek/deepseek-v4-flash" ,session_id: sessionId, message }),
    });
    if (!res.ok) throw new Error(`Backend respondió ${res.status}`);
    return await res.json() as { status: string; message: string; bpmn_xml?: string | null };
}