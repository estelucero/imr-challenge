export type ChatProvider = "openai" | "openrouter";

export type ChatModel = {
    id: string;
    provider: ChatProvider;
    name: string;
    vendor: string;
};

// OpenAI no tiene API pública de modelos (/v1/models requiere key),
// así que mantenemos una lista curada de los modelos de chat vigentes.
const OPENAI_MODELS: ChatModel[] = [
    { id: "gpt-5", provider: "openai", name: "GPT-5", vendor: "OpenAI" },
    { id: "gpt-5-mini", provider: "openai", name: "GPT-5 mini", vendor: "OpenAI" },
    { id: "gpt-5-nano", provider: "openai", name: "GPT-5 nano", vendor: "OpenAI" },
    { id: "gpt-4.1", provider: "openai", name: "GPT-4.1", vendor: "OpenAI" },
    { id: "gpt-4.1-mini", provider: "openai", name: "GPT-4.1 mini", vendor: "OpenAI" },
    { id: "gpt-4o", provider: "openai", name: "GPT-4o", vendor: "OpenAI" },
    { id: "gpt-4o-mini", provider: "openai", name: "GPT-4o mini", vendor: "OpenAI" },
];

export const DEFAULT_MODEL: ChatModel = {
    id: "deepseek/deepseek-v4-flash",
    provider: "openrouter",
    name: "DeepSeek V4 Flash",
    vendor: "DeepSeek",
};

// Etiquetas legibles para el vendor de cada slug de OpenRouter.
const VENDOR_LABELS: Record<string, string> = {
    openai: "OpenAI",
    anthropic: "Anthropic",
    google: "Google",
    deepseek: "DeepSeek",
    "x-ai": "xAI",
    mistralai: "Mistral AI",
    qwen: "Qwen",
    "meta-llama": "Meta Llama",
    moonshotai: "Moonshot AI",
    "z-ai": "Z.AI",
    amazon: "Amazon",
    cohere: "Cohere",
};

const OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models";
const OPENROUTER_PROVIDERS = new Set([
    "openai",
    "anthropic",
    "google",
    "deepseek",
    "x-ai",
    "mistralai",
    "qwen",
    "meta-llama",
    "moonshotai",
    "z-ai",
    "amazon",
    "cohere",
]);

// OpenRouter publica su lista de modelos en una API pública (sin auth y con
// CORS abierto), así que el front puede consultarla directamente. Filtramos a
// modelos de chat de texto, descartamos variantes (`:free`, `:beta`, ...) y
// nos quedamos con proveedores conocidos, para que los IDs que llegan al
// backend sean siempre válidos.
let openRouterModelsCache: ChatModel[] | null = null;

export async function fetchOpenRouterModels(): Promise<ChatModel[]> {
    if (openRouterModelsCache) return openRouterModelsCache;

    const res = await fetch(OPENROUTER_MODELS_URL);
    if (!res.ok) throw new Error(`OpenRouter respondió ${res.status}`);

    const data = (await res.json()) as {
        data: {
            id: string;
            name: string;
            architecture: { output_modalities: string[] };
        }[];
    };

    const models = data.data
        .filter(
            (m) =>
                !m.id.includes(":") &&
                !/-exp$/.test(m.id) &&
                !/guard|safeguard/.test(m.id) &&
                m.architecture.output_modalities.length === 1 &&
                m.architecture.output_modalities[0] === "text" &&
                OPENROUTER_PROVIDERS.has(m.id.split("/")[0]),
        )
        .map((m) => {
            const slug = m.id.split("/", 1)[0];
            const vendor = VENDOR_LABELS[slug] ?? slug;

            return {
                id: m.id,
                provider: "openrouter" as const,
                // La API devuelve nombres tipo "OpenAI: GPT-5 mini"; quitamos
                // el prefijo para que el nombre puro del modelo quede visible.
                name: m.name.replace(/^[^:]+:\s*/, "") || m.name,
                vendor: vendor,
            };
        })
        .sort((a, b) => a.name.localeCompare(b.name));

    openRouterModelsCache = models;
    return models;
}

export async function getModels(): Promise<ChatModel[]> {
    const [openRouterModels] = await Promise.all([
        fetchOpenRouterModels().catch(() => [] as ChatModel[]),
    ]);
    return [...OPENAI_MODELS, ...openRouterModels];
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
