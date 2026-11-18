export type ChatProvider = "openai" | "openrouter";

export type ChatModel = {
    id: string;
    provider: ChatProvider;
    name: string;
    vendor: string;
};

// Lista curada de la familia GPT que ofrezco en el selector. De cada familia
// (Luna, Sol, Terra, Astra) expongo la generación más nueva disponible en
// base + Pro. Desde este único array derivan las listas de OpenAI (ids sin
// prefijo) y de OpenRouter (ids con el prefijo del vendor).
const GPT_MODELS = [
    { id: "gpt-6-luna", name: "GPT-6 Luna" },
    { id: "gpt-6-luna-pro", name: "GPT-6 Luna Pro" },
    { id: "gpt-6.2-sol", name: "GPT-6.2 Sol" },
    { id: "gpt-6.2-sol-pro", name: "GPT-6.2 Sol Pro" },
    { id: "gpt-6.1-terra", name: "GPT-6.1 Terra" },
    { id: "gpt-6.1-terra-pro", name: "GPT-6.1 Terra Pro" },
    { id: "gpt-6.2-astra", name: "GPT-6.2 Astra" },
    { id: "gpt-6.2-astra-pro", name: "GPT-6.2 Astra Pro" },
];

const OPENAI_MODELS: ChatModel[] = GPT_MODELS.map((m) => ({
    id: m.id,
    provider: "openai" as const,
    name: m.name,
    vendor: "OpenAI",
}));

const OPENROUTER_MODELS: ChatModel[] = GPT_MODELS.map((m) => ({
    id: "openai/" + m.id,
    provider: "openrouter" as const,
    name: m.name,
    vendor: "OpenAI",
}));

export const DEFAULT_MODEL: ChatModel = {
    id: "openai/gpt-6-luna",
    provider: "openrouter",
    name: "GPT-6 Luna",
    vendor: "OpenAI",
};

export async function getModels(): Promise<ChatModel[]> {
    return [...OPENAI_MODELS, ...OPENROUTER_MODELS];
}

const STORAGE_KEY = "imr-chat-model";

export function readSelectedModel(models: ChatModel[]): ChatModel {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const saved = JSON.parse(raw) as { id?: string; provider?: string };
            const match = models.find(
                (m) =>
                    m.id === saved.id && m.provider === saved.provider,
            );
            if (match) return match;
        }
    } catch {
        // localStorage corrupto o inaccesible: usamos el default.
    }
    return DEFAULT_MODEL;
}

export function writeSelectedModel(model: ChatModel) {
    try {
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ id: model.id, provider: model.provider }),
        );
    } catch {
        // Sin acceso a localStorage: la selección no persiste, no es grave.
    }
}
