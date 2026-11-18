"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import {
    CheckIcon,
    DownloadIcon,
    SaveIcon,
    WorkflowIcon,
    XIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { saveDiagram, type SavedDiagram } from "@/lib/bpmn/storage";
import { getDate } from "@/lib/date";

const BpmnModeler = dynamic(() => import("@/components/bpmn/bpmn-modeler"), {
    ssr: false,
    loading: () => (
        <div className="flex h-full items-center justify-center p-4">
            <Skeleton className="h-full w-full" />
        </div>
    ),
});

export type EditorDiagram = {
    id: string;
    name: string;
    xml: string;
};

type BpmnEditorDialogProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    diagram: EditorDiagram | null;
    /** Notifica el xml editado para sincronizar en vivo (ej. preview del chat). */
    onXmlChange?: (xml: string) => void;
    /** Se llama después de guardar en el storage. */
    onSaved?: (diagram: SavedDiagram) => void;
};

export function BpmnEditorDialog({
    open,
    onOpenChange,
    diagram,
    onXmlChange,
    onSaved,
}: BpmnEditorDialogProps) {
    // Snapshot del xml al montar: el modeler recibe siempre este xml de
    // origen y así no se re-importa (ni pierde zoom/undo) con cada edición.
    // Los padres pasan key={diagram.id} para que el estado se reinicie
    // cuando se abre otro diagrama.
    const [sourceXml] = React.useState<string | null>(diagram?.xml ?? null);
    const [editedXml, setEditedXml] = React.useState<string | null>(null);
    const [name, setName] = React.useState(diagram?.name ?? "");
    const [justSaved, setJustSaved] = React.useState(false);

    // Cada vez que se abre el modal, el nombre arranca con la fecha y hora.
    // Ajuste de estado durante el render (patrón de React para props cambiantes).
    const [prevOpen, setPrevOpen] = React.useState(open);
    if (open !== prevOpen) {
        setPrevOpen(open);
        if (open) {
            setName(getDate());
        }
    }

    const savedTimerRef = React.useRef<number | undefined>(undefined);
    const onXmlChangeRef = React.useRef(onXmlChange);
    const onSavedRef = React.useRef(onSaved);

    React.useEffect(() => {
        onXmlChangeRef.current = onXmlChange;
    }, [onXmlChange]);

    React.useEffect(() => {
        onSavedRef.current = onSaved;
    }, [onSaved]);

    React.useEffect(() => {
        return () => window.clearTimeout(savedTimerRef.current);
    }, []);

    const currentXml = editedXml ?? sourceXml;

    function handleXmlChange(xml: string) {
        setEditedXml(xml);
        onXmlChangeRef.current?.(xml);
    }

    function handleSave() {
        if (!diagram || !currentXml) return;

        const saved = saveDiagram({
            id: diagram.id,
            name: name.trim() || diagram.name || "Sin título",
            xml: currentXml,
        });
        if (!saved) return;

        setJustSaved(true);
        window.clearTimeout(savedTimerRef.current);
        savedTimerRef.current = window.setTimeout(() => {
            setJustSaved(false);
        }, 1600);

        onSavedRef.current?.(saved);
    }

    function download() {
        if (!currentXml) return;

        const fileName =
            (name.trim() || diagram?.name || "proceso")
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, "-")
                .replace(/^-+|-+$/g, "") || "proceso";

        const blob = new Blob([currentXml], { type: "application/xml" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${fileName}.bpmn`;
        link.click();
        URL.revokeObjectURL(url);
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent
                showCloseButton={false}
                className="h-[85dvh] w-[90vw] max-w-5xl gap-0 p-0"
            >
                <DialogHeader className="flex-row items-center gap-2 border-b p-3">
                    <WorkflowIcon className="size-4 shrink-0 text-muted-foreground" />
                    <DialogTitle className="min-w-0 truncate text-sm font-medium">
                        {name.trim() || diagram?.name || "Diagrama BPMN"}
                    </DialogTitle>
                    <div className="ml-auto flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={download}
                            disabled={!currentXml}
                        >
                            <DownloadIcon />
                            <span className="sr-only">Descargar BPMN</span>
                        </Button>
                        <DialogClose
                            render={<Button variant="ghost" size="icon-sm" />}
                        >
                            <XIcon
                            />
                            <span className="sr-only">Cerrar</span>
                        </DialogClose>
                    </div>
                </DialogHeader>

                <div className="min-h-0 flex-1">
                    {sourceXml && (
                        <BpmnModeler
                            xml={sourceXml}
                            onXmlChange={handleXmlChange}
                            className="h-full w-full"
                        />
                    )}
                </div>

                <DialogFooter className="flex-row items-center gap-2 border-t p-3">
                    <Input
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Nombre del proceso"
                        maxLength={80}
                        className="flex-1"
                    />
                    <Button onClick={handleSave} disabled={!currentXml}>
                        {justSaved ? <CheckIcon /> : <SaveIcon />}
                        {justSaved ? "Guardado" : "Guardar"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
