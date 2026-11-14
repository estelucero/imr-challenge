"use client";

import * as React from "react";
import Viewer from "bpmn-js/lib/Viewer";

type BpmnViewerProps = {
    xml: string;
    className?: string;
};

/**
 * Vista previa read-only del diagrama, para embeber en el chat.
 * Usa el Viewer (no el NavigatedViewer) a propósito: sin pan/zoom,
 * así la rueda del mouse no le secuestra el scroll a la conversación.
 */
export default function BpmnViewer({ xml, className }: BpmnViewerProps) {
    const containerRef = React.useRef<HTMLDivElement>(null);
    const viewerRef = React.useRef<Viewer | null>(null);

    // El viewer se crea una sola vez, igual que el modeler.
    React.useEffect(() => {
        if (!containerRef.current) return;

        const viewer = new Viewer({ container: containerRef.current });
        viewerRef.current = viewer;

        return () => {
            viewer.destroy();
            viewerRef.current = null;
        };
    }, []);

    // Re-importa cuando llega un xml nuevo (por ejemplo, cuando se
    // edita el diagrama en el modal y el cambio se sincroniza en vivo).
    React.useEffect(() => {
        const viewer = viewerRef.current;
        if (!viewer || !xml) return;

        let cancelled = false;

        (async () => {
            try {
                await viewer.importXML(xml);
                if (cancelled) return;

                const canvas = viewer.get("canvas") as {
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
