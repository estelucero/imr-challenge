"use client";
import * as React from "react";
import { ArrowUpIcon } from "lucide-react";

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
    MessageScrollerProvider,
    MessageScrollerViewport,
} from "@/components/ui/message-scroller";
import { buildMockBpmn } from "@/lib/bpmn/mock";

type ChatMessage = {
    id: string;
    role: "user" | "assistant";
    text: string;
};

export function Chat({ onDiagram }: { onDiagram?: (xml: string) => void }) {
    const [messages, setMessages] = React.useState<ChatMessage[]>([]);
    const [draft, setDraft] = React.useState("");
    const [isLoading, setIsLoading] = React.useState(false);
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
                    text: `Listo, generé el proceso para "${text}". Podés editarlo en el panel de la derecha.`,
                },
            ]);
            onDiagram?.(xml);
            setIsLoading(false);
        }, 900);
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
        </MessageScrollerProvider>
    );
}
