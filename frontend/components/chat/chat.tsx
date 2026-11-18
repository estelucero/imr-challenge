"use client";
import * as React from "react";
import dynamic from "next/dynamic";
import { ArrowUpIcon, PencilIcon, WorkflowIcon } from "lucide-react";
import { type ChatMessage } from "@/lib/chat/sessions";

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
import { Markdown } from "@/components/ui/markdown";
import { Message, MessageContent } from "@/components/ui/message";
import {
    MessageScroller,
    MessageScrollerButton,
    MessageScrollerContent,
    MessageScrollerItem,
    MessageScrollerViewport,
    MessageScrollerProvider,
} from "@/components/ui/message-scroller";
import { ModelSelector } from "@/components/chat/model-selector";
import { Loader } from "@/components/ui/loader";
import { Skeleton } from "@/components/ui/skeleton";
import { sendChat } from "@/lib/chat/api";
import {
    DEFAULT_MODEL,
    getModels,
    readSelectedModel,
    writeSelectedModel,
    type ChatModel,
} from "@/lib/chat/models";

const BpmnViewer = dynamic(() => import("@/components/bpmn/bpmn-viewer"), {
    ssr: false,
    loading: () => <Skeleton className="h-full w-full" />,
});

type ChatProps = {
    messages: ChatMessage[];
    onUserMessage: (text: ChatMessage) => string;
    onAssistantMessage: (message: ChatMessage) => void;
    onUpdateBpmnXml: (messageId: string, xml: string) => void;
};

export function Chat({
    messages,
    onUserMessage,
    onAssistantMessage,
    onUpdateBpmnXml,
}: ChatProps) {
    const [draft, setDraft] = React.useState("");
    const [isLoading, setIsLoading] = React.useState(false);
    const [editorOpen, setEditorOpen] = React.useState(false);
    const [active, setActive] = React.useState<{
        messageId: string;
        diagram: EditorDiagram;
    } | null>(null);
    const [models, setModels] = React.useState<ChatModel[]>([]);
    const [selectedModel, setSelectedModel] = React.useState<ChatModel>(DEFAULT_MODEL);
    const formRef = React.useRef<HTMLFormElement>(null);

    React.useEffect(() => {
        let cancelled = false;

        getModels().then((available) => {
            if (cancelled) return;
            setModels(available);
            setSelectedModel(readSelectedModel(available));
        });

        return () => {
            cancelled = true;
        };
    }, []);

    function selectModel(model: ChatModel) {
        setSelectedModel(model);
        writeSelectedModel(model);
    }

    const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const text = draft.trim();
        if (!text || isLoading) return;
        const sessionId = onUserMessage({ id: crypto.randomUUID(), role: "user", text });
        setDraft("");
        setIsLoading(true);
        try {
            const res = await sendChat(sessionId, text, selectedModel);
            onAssistantMessage({
                id: crypto.randomUUID(), role: "assistant",
                text: res.message,
                bpmn: res.bpmn_xml ? { id: crypto.randomUUID(), name: text, xml: res.bpmn_xml } : undefined,
            });
        } catch {
            onAssistantMessage({ id: crypto.randomUUID(), role: "assistant", text: "No se pudo contactar al servidor. Intentá de nuevo." });
        } finally {
            setIsLoading(false);
        }
    };

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
        onUpdateBpmnXml(messageId, xml);
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
                                                            <BubbleText message={message} />
                                                        </BubbleContent>
                                                    </Bubble>
                                                    {message.bpmn && (
                                                        <DiagramPreview
                                                            xml={
                                                                message.bpmn.xml
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
                                                            <Loader />
                                                        </BubbleContent>
                                                    </Bubble>
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
                                <ModelSelector
                                    models={models}
                                    value={selectedModel}
                                    onChange={selectModel}
                                />
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

function BubbleText({ message }: { message: ChatMessage }) {
    if (message.role === "assistant") {
        return <Markdown>{message.text}</Markdown>;
    }

    return <>{message.text}</>;
}

function DiagramPreview({ xml, onOpen }: { xml: string; onOpen: () => void }) {
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
