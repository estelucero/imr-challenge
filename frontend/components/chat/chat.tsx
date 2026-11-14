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

type ChatMessage = {
    id: string;
    role: "user" | "assistant";
    text: string;
};

export function Chat() {
    const [messages, setMessages] = React.useState<ChatMessage[]>([]);
    const [draft, setDraft] = React.useState("");
    const formRef = React.useRef<HTMLFormElement>(null);

    function onSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        const text = draft.trim();
        if (!text) return;

        setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "user", text },
            {
                id: crypto.randomUUID(),
                role: "assistant",
                text: "Todavía no estoy conectado al servidor.",
            },
        ]);
        setDraft("");
    }

    return (
        <MessageScrollerProvider autoScroll>
            <div className="flex h-full min-h-0 flex-col">
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
                                    disabled={!draft.trim()}
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
