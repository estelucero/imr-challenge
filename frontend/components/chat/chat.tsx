"use client";
import * as React from "react";
import dynamic from "next/dynamic";
import { ArrowUpIcon, PencilIcon, WorkflowIcon } from "lucide-react";

import {
    BpmnEditorDialog,
    type EditorDiagram,
} from "@/components/bpmn/bpmn-editor-dialog";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import {
    InputGroup,
    InputGroupAddon,
    InputGroupButton,
    InputGroupTextarea,
} from "@/components/ui/input-group";
import { Message, MessageContent } from "@/components/ui/message";
import {
    MessageScroller,
    MessageScrollerButton,
    MessageScrollerContent,
    MessageScrollerItem,
    MessageScrollerViewport,
    MessageScrollerProvider,
} from "@/components/ui/message-scroller";
import { Skeleton } from "@/components/ui/skeleton";
import { buildMockBpmn } from "@/lib/bpmn/mock";

const BpmnViewer = dynamic(() => import("@/components/bpmn/bpmn-viewer"), {
    ssr: false,
    loading: () => <Skeleton className="h-full w-full" />,
});

type ChatMessageBpmn = {
    id: string;
    name: string;
    xml: string;
};

type ChatMessage = {
    id: string;
    role: "user" | "assistant";
    text: string;
    bpmn?: ChatMessageBpmn;
};

export function Chat() {
    const [messages, setMessages] = React.useState<ChatMessage[]>([]);
    const [draft, setDraft] = React.useState("");
    const [isLoading, setIsLoading] = React.useState(false);
    const [editorOpen, setEditorOpen] = React.useState(false);
    const [active, setActive] = React.useState<{
        messageId: string;
        diagram: EditorDiagram;
    } | null>(null);
    const formRef = React.useRef<HTMLFormElement>(null);

    function onSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        const text = draft.trim();
        if (!text || isLoading) return;

        setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "user", text },
        ]);
        setDraft("");
        setIsLoading(true);

        const xml = buildMockBpmn(text);

        // Mock de la respuesta del chatbot: cuando exista el backend,
        // reemplazar por un fetch que devuelva { text, bpmnXml }.
        window.setTimeout(() => {
            setMessages((prev) => [
                ...prev,
                {
                    id: crypto.randomUUID(),
                    role: "assistant",
                    text: `Listo, generé el proceso para "${text}". Tocá el diagrama para editarlo.`,
                    bpmn: { id: crypto.randomUUID(), name: text, xml },
                },
            ]);
            setIsLoading(false);
        }, 900);
    }

    function openEditor(message: ChatMessage) {
        if (!message.bpmn) return;

        setActive({
            messageId: message.id,
            diagram: {
                id: message.bpmn.id,
                name: message.bpmn.name,
                xml: message.bpmn.xml,
            },
        });
        setEditorOpen(true);
    }

    // Sync en vivo: cada edición del modeler actualiza el xml del mensaje,
    // así el preview del chat refleja siempre la versión actual.
    function updateActiveDiagramXml(xml: string) {
        if (!active) return;

        const messageId = active.messageId;
        setMessages((prev) =>
            prev.map((message) =>
                message.id === messageId && message.bpmn
                    ? { ...message, bpmn: { ...message.bpmn, xml } }
                    : message,
            ),
        );
    }

    return (
        <MessageScrollerProvider autoScroll>
            <div className="flex h-full min-h-0 w-full flex-col overflow-hidden">
                <div className="min-h-0 flex-1">
                    {messages.length === 0 ? (
                        <div className="flex h-full items-center justify-center p-8 text-center text-muted-foreground">
                            Escribí un mensaje para empezar.
                        </div>
                    ) : (
                        <MessageScroller>
                            <MessageScrollerViewport>
                                <MessageScrollerContent className="p-4">
                                    {messages.map((message) => (
                                        <MessageScrollerItem
                                            key={message.id}
                                            messageId={message.id}
                                            scrollAnchor={
                                                message.role === "user"
                                            }
                                        >
                                            <Message
                                                align={
                                                    message.role === "user"
                                                        ? "end"
                                                        : "start"
                                                }
                                            >
                                                <MessageContent>
                                                    <Bubble
                                                        align={
                                                            message.role ===
                                                            "user"
                                                                ? "end"
                                                                : "start"
                                                        }
                                                        variant={
                                                            message.role ===
                                                            "user"
                                                                ? "muted"
                                                                : "secondary"
                                                        }
                                                    >
                                                        <BubbleContent>
                                                            {message.text}
                                                        </BubbleContent>
                                                    </Bubble>
                                                    {message.bpmn && (
                                                        <DiagramPreview
                                                            xml={
                                                                message.bpmn
                                                                    .xml
                                                            }
                                                            onOpen={() =>
                                                                openEditor(
                                                                    message,
                                                                )
                                                            }
                                                        />
                                                    )}
                                                </MessageContent>
                                            </Message>
                                        </MessageScrollerItem>
                                    ))}
                                    {isLoading && (
                                        <MessageScrollerItem
                                            messageId="loading"
                                            scrollAnchor
                                        >
                                            <Message align="start">
                                                <MessageContent>
                                                    <Bubble
                                                        align="start"
                                                        variant="secondary"
                                                    >
                                                        <BubbleContent className="text-muted-foreground">
                                                            Generando diagrama...
                                                        </BubbleContent>
                                                    </Bubble>
                                                    <Skeleton className="h-52 w-80 max-w-full rounded-xl" />
                                                </MessageContent>
                                            </Message>
                                        </MessageScrollerItem>
                                    )}
                                </MessageScrollerContent>
                            </MessageScrollerViewport>
                            <MessageScrollerButton />
                        </MessageScroller>
                    )}
                </div>

                <div className="border-t p-4">
                    <form ref={formRef} onSubmit={onSubmit}>
                        <InputGroup>
                            <InputGroupTextarea
                                value={draft}
                                onChange={(event) =>
                                    setDraft(event.target.value)
                                }
                                placeholder="Describí tu proceso de negocio..."
                                className="min-h-14"
                                onKeyDown={(event) => {
                                    if (
                                        event.key === "Enter" &&
                                        !event.shiftKey
                                    ) {
                                        event.preventDefault();
                                        formRef.current?.requestSubmit();
                                    }
                                }}
                            />
                            <InputGroupAddon align="block-end">
                                <InputGroupButton
                                    type="submit"
                                    size="icon-sm"
                                    className="ml-auto"
                                    disabled={!draft.trim() || isLoading}
                                >
                                    <ArrowUpIcon />
                                    <span className="sr-only">Enviar</span>
                                </InputGroupButton>
                            </InputGroupAddon>
                        </InputGroup>
                    </form>
                </div>
            </div>

            <BpmnEditorDialog
                key={active?.diagram.id ?? "none"}
                open={editorOpen}
                onOpenChange={setEditorOpen}
                diagram={active?.diagram ?? null}
                onXmlChange={updateActiveDiagramXml}
            />
        </MessageScrollerProvider>
    );
}

function DiagramPreview({
    xml,
    onOpen,
}: {
    xml: string;
    onOpen: () => void;
}) {
    return (
        <div className="group/preview w-80 max-w-full overflow-hidden rounded-xl border border-border bg-card transition-colors hover:border-ring/60">
            <button
                type="button"
                onClick={onOpen}
                aria-label="Abrir el editor del diagrama"
                className="relative block h-52 w-full cursor-pointer outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
                <BpmnViewer xml={xml} className="h-full w-full" />
            </button>
            <div className="flex items-center gap-1.5 border-t px-3 py-1.5 text-xs text-muted-foreground">
                <WorkflowIcon className="size-3.5 shrink-0" />
                <span className="truncate">Diagrama BPMN</span>
                <span className="ml-auto flex items-center gap-1 transition-colors group-hover/preview:text-foreground">
                    <PencilIcon className="size-3" />
                    Editar
                </span>
            </div>
        </div>
    );
}
