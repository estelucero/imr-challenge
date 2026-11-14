"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { DownloadIcon, WorkflowIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const BpmnModeler = dynamic(() => import("@/components/bpmn/bpmn-modeler"), {
    ssr: false,
    loading: () => (
        <div className="flex h-full items-center justify-center p-4">
            <Skeleton className="h-full w-full" />
        </div>
    ),
});

type BpmnPanelProps = {
    xml: string | null;
};

export function BpmnPanel({ xml }: BpmnPanelProps) {
    // El XML que exporta el modeler se guarda aparte del que viene del
    // chat para no re-importar (y resetear el canvas) en cada edición.
    // Se guarda junto al xml de origen: si llega un diagrama nuevo, el
    // editado viejo deja de aplicar sin necesidad de un useEffect.
    const [edited, setEdited] = React.useState<{
        source: string;
        xml: string;
    } | null>(null);

    const editedXml = edited && edited.source === xml ? edited.xml : null;
    const currentXml = editedXml ?? xml;

    function download() {
        if (!currentXml) return;

        const blob = new Blob([currentXml], { type: "application/xml" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "proceso.bpmn";
        link.click();
        URL.revokeObjectURL(url);
    }

    return (
        <div className="flex h-full min-h-0 flex-col">
            <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
                <WorkflowIcon className="size-4" />
                <h2 className="text-sm font-medium">Diagrama BPMN</h2>
                {xml && (
                    <span className="text-xs text-muted-foreground">
                        editable
                    </span>
                )}
                <Button
                    variant="ghost"
                    size="icon-sm"
                    className="ml-auto"
                    onClick={download}
                    disabled={!currentXml}
                >
                    <DownloadIcon />
                    <span className="sr-only">Descargar BPMN</span>
                </Button>
            </header>

            <div className="min-h-0 flex-1">
                {xml ? (
                    <BpmnModeler
                        xml={xml}
                        onXmlChange={(value) =>
                            setEdited({ source: xml, xml: value })
                        }
                        className="h-full w-full"
                    />
                ) : (
                    <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center text-sm text-muted-foreground">
                        <WorkflowIcon className="size-8" />
                        <p>
                            Pedile un proceso al chat y el diagrama va a
                            aparecer acá.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
