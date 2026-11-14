"use client";

import * as React from "react";
import Modeler from "bpmn-js/lib/Modeler";

type BpmnModelerProps = {
    xml: string;
    onXmlChange?: (xml: string) => void;
    className?: string;
};

export default function BpmnModeler({
    xml,
    onXmlChange,
    className,
}: BpmnModelerProps) {
    const containerRef = React.useRef<HTMLDivElement>(null);
    const modelerRef = React.useRef<Modeler | null>(null);
    const onXmlChangeRef = React.useRef(onXmlChange);

    React.useEffect(() => {
        onXmlChangeRef.current = onXmlChange;
    }, [onXmlChange]);

    // El modeler se crea una sola vez. Si se recreara en cada render
    // perderíamos la posición del canvas y el historial de undo/redo.
    React.useEffect(() => {
        if (!containerRef.current) return;

        const modeler = new Modeler({ container: containerRef.current });
        modelerRef.current = modeler;

        let saveTimer: number | undefined;

        modeler.on("commandStack.changed", () => {
            window.clearTimeout(saveTimer);
            saveTimer = window.setTimeout(async () => {
                try {
                    const { xml } = await modeler.saveXML({ format: true });
                    if (xml) onXmlChangeRef.current?.(xml);
                } catch (error) {
                    console.error("No se pudo exportar el XML", error);
                }
            }, 400);
        });

        return () => {
            window.clearTimeout(saveTimer);
            modeler.destroy();
            modelerRef.current = null;
        };
    }, []);

    // Importar cuando llega un diagrama nuevo desde el chat.
    // Ojo: no se vuelve a importar cuando el usuario edita, porque el
    // xml editado vive en otro estado (ver bpmn-panel.tsx).
    React.useEffect(() => {
        const modeler = modelerRef.current;
        if (!modeler || !xml) return;

        let cancelled = false;

        (async () => {
            try {
                await modeler.importXML(xml);
                if (cancelled) return;

                const canvas = modeler.get("canvas") as {
                    zoom: (value: string | number) => void;
                };
                canvas.zoom("fit-viewport");
            } catch (error) {
                console.error("XML BPMN inválido", error);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [xml]);

    return <div ref={containerRef} className={className} />;
}
