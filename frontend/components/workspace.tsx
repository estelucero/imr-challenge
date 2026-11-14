"use client";

import { SavedDiagramsSheet } from "@/components/bpmn/saved-diagrams-sheet";
import { AppSidebar } from "@/components/chat/sidebar";
import { Chat } from "@/components/chat/chat";
import {
    SidebarInset,
    SidebarProvider,
    SidebarTrigger,
} from "@/components/ui/sidebar";
import { useChatSessions } from "@/hooks/use-chat-sessions";

export function Workspace() {
    const {
        sessions,
        activeId,
        activeSession,
        newChat,
        selectSession,
        deleteSession,
        addMessage,
        updateMessageBpmn,
    } = useChatSessions();

    return (
        <SidebarProvider className="h-dvh overflow-hidden">
            <AppSidebar
                sessions={sessions}
                activeId={activeId}
                onNewChat={newChat}
                onSelect={selectSession}
                onDelete={deleteSession}
            />

            <SidebarInset className="min-w-0 overflow-hidden">
                <header className="flex h-12 shrink-0 items-center gap-2 border-b px-2">
                    <SidebarTrigger />
                    <div className="ml-auto">
                        <SavedDiagramsSheet />
                    </div>
                </header>

                <div className="min-h-0 flex-1">
                    <div className="flex h-full min-h-0 w-full overflow-hidden">
                        <div className="flex h-full min-h-0 flex-1 flex-col">
                            <Chat
                                messages={activeSession?.messages ?? []}
                                onUserMessage={addMessage}
                                onAssistantMessage={addMessage}
                                onUpdateBpmnXml={updateMessageBpmn}
                            />
                        </div>
                    </div>
                </div>
            </SidebarInset>
        </SidebarProvider>
    );
}
