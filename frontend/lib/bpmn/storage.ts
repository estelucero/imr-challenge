export type SavedDiagram = {
    id: string;
    name: string;
    xml: string;
    updatedAt: number;
};

const STORAGE_KEY = "imr-bpmn-diagrams";

function isSavedDiagram(value: unknown): value is SavedDiagram {
    if (typeof value !== "object" || value === null) return false;

    const item = value as Record<string, unknown>;
    return (
        typeof item.id === "string" &&
        typeof item.name === "string" &&
        typeof item.xml === "string" &&
        typeof item.updatedAt === "number"
    );
}

function readAll(): SavedDiagram[] {
    if (typeof window === "undefined" || !window.localStorage) return [];

    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return [];

        const parsed: unknown = JSON.parse(raw);
        if (!Array.isArray(parsed)) return [];

        return parsed.filter(isSavedDiagram);
    } catch (error) {
        console.error("No se pudo leer la lista de BPMNs guardados", error);
        return [];
    }
}

function writeAll(diagrams: SavedDiagram[]): boolean {
    if (typeof window === "undefined" || !window.localStorage) return false;

    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(diagrams));
        return true;
    } catch (error) {
        console.error("No se pudo guardar el BPMN en el storage", error);
        return false;
    }
}

/** Lista los diagramas guardados, del más reciente al más viejo. */
export function listDiagrams(): SavedDiagram[] {
    return readAll().sort((a, b) => b.updatedAt - a.updatedAt);
}

/** Crea o actualiza (por id) un diagrama en el storage. */
export function saveDiagram(input: {
    id: string;
    name: string;
    xml: string;
}): SavedDiagram | null {
    const rest = readAll().filter((diagram) => diagram.id !== input.id);
    const saved: SavedDiagram = { ...input, updatedAt: Date.now() };

    return writeAll([saved, ...rest]) ? saved : null;
}

export function removeDiagram(id: string): boolean {
    const all = readAll();
    const rest = all.filter((diagram) => diagram.id !== id);
    if (rest.length === all.length) return false;

    return writeAll(rest);
}
