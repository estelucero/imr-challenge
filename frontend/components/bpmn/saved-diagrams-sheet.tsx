"use client";

import * as React from "react";
import { FolderOpenIcon, TrashIcon, WorkflowIcon } from "lucide-react";

import {
    BpmnEditorDialog,
    type EditorDiagram,
} from "@/components/bpmn/bpmn-editor-dialog";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
import {
    listDiagrams,
    removeDiagram,
    type SavedDiagram,
} from "@/lib/bpmn/storage";

export function SavedDiagramsSheet() {
    const [listOpen, setListOpen] = React.useState(false);
    const [editorOpen, setEditorOpen] = React.useState(false);
    const [diagrams, setDiagrams] = React.useState<SavedDiagram[]>([]);
    const [editing, setEditing] = React.useState<EditorDiagram | null>(null);
    const [deleteArmId, setDeleteArmId] = React.useState<string | null>(null);

    const deleteTimerRef = React.useRef<number | undefined>(undefined);

    React.useEffect(() => {
        return () => window.clearTimeout(deleteTimerRef.current);
    }, []);

    // El storage solo existe en el cliente: se lee cada vez que se abre
    // el sheet para no romper la hidratación y mostrar datos frescos.
    function handleListOpenChange(open: boolean) {
        setListOpen(open);
        if (open) setDiagrams(listDiagrams());
    }

    function refresh() {
        setDiagrams(listDiagrams());
    }

    function openItem(item: SavedDiagram) {
        setEditing({ id: item.id, name: item.name, xml: item.xml });
        setEditorOpen(true);
        setListOpen(false);
    }

    // Borrado en dos pasos: el primer click arma el botón y el segundo
    // confirma. Se desarma solo a los 2.5s.
    function handleDelete(id: string) {
        window.clearTimeout(deleteTimerRef.current);

        if (deleteArmId !== id) {
            setDeleteArmId(id);
            deleteTimerRef.current = window.setTimeout(() => {
                setDeleteArmId(null);
            }, 2500);
            return;
        }

        setDeleteArmId(null);
        removeDiagram(id);
        refresh();
    }

    function formatDate(timestamp: number) {
        return new Date(timestamp).toLocaleString("es-AR", {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    return (
        <>
            <Sheet open={listOpen} onOpenChange={handleListOpenChange}>
                <SheetTrigger render={<Button variant="outline" size="sm" />}>
                    <FolderOpenIcon
                    />
                    Mis BPMN
                </SheetTrigger>
                <SheetContent className="gap-0">
                    <SheetHeader className="border-b">
                        <SheetTitle>Mis BPMN</SheetTitle>
                        <SheetDescription>
                            Diagramas guardados en este navegador.
                        </SheetDescription>
                    </SheetHeader>

                    <div className="min-h-0 flex-1 overflow-y-auto p-2">
                        {diagrams.length === 0 ? (
                            <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center text-sm text-muted-foreground">
                                <WorkflowIcon className="size-8" />
                                <p>
                                    Todavía no guardaste ningún BPMN.
                                    Generá uno desde el chat y toca Guardar.
                                </p>
                            </div>
                        ) : (
                            <ul className="flex flex-col gap-1">
                                {diagrams.map((item) => (
                                    <li
                                        key={item.id}
                                        className="flex items-center gap-1 rounded-lg p-1 hover:bg-muted"
                                    >
                                        <button
                                            type="button"
                                            onClick={() => openItem(item)}
                                            className="flex min-w-0 flex-1 cursor-pointer flex-col items-start gap-0.5 rounded-md px-2 py-1.5 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                                        >
                                            <span className="w-full truncate text-sm font-medium">
                                                {item.name}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                {formatDate(item.updatedAt)}
                                            </span>
                                        </button>
                                        <Button
                                            variant={
                                                deleteArmId === item.id
                                                    ? "destructive"
                                                    : "ghost"
                                            }
                                            size="icon-sm"
                                            title={
                                                deleteArmId === item.id
                                                    ? "Confirmar eliminación"
                                                    : "Eliminar"
                                            }
                                            aria-label="Eliminar diagrama"
                                            onClick={() =>
                                                handleDelete(item.id)
                                            }
                                        >
                                            <TrashIcon
                                            />
                                        </Button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </SheetContent>
            </Sheet>

            <BpmnEditorDialog
                key={editing?.id ?? "none"}
                open={editorOpen}
                onOpenChange={setEditorOpen}
                diagram={editing}
                onSaved={refresh}
            />
        </>
    );
}
