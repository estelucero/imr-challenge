/** Fecha y hora en formato es-AR (DD/MM/YYYY, HH:mm:ss). */
export function getDate(): string {
    return new Date().toLocaleString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    });
}
