"use client";
import * as React from "react";
import { MessageSquareIcon, PlusIcon, TrashIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuAction,
    SidebarMenuButton,
    SidebarMenuItem,
    useSidebar,
} from "@/components/ui/sidebar";
import type { ChatSession } from "@/lib/chat/sessions";

type AppSidebarProps = {
    sessions: ChatSession[];
    activeId: string | null;
    onNewChat: () => void;
    onSelect: (id: string) => void;
    onDelete: (id: string) => void;
};

export function AppSidebar({
    sessions,
    activeId,
    onNewChat,
    onSelect,
    onDelete,
}: AppSidebarProps) {
    const { isMobile, setOpenMobile } = useSidebar();
    const [deleteArmId, setDeleteArmId] = React.useState<string | null>(null);
    const deleteTimerRef = React.useRef<number | undefined>(undefined);

    React.useEffect(() => {
        return () => window.clearTimeout(deleteTimerRef.current);
    }, []);

    function startNewChat() {
        onNewChat();
        if (isMobile) setOpenMobile(false);
    }

    function select(id: string) {
        onSelect(id);
        if (isMobile) setOpenMobile(false);
    }

    // Borrado en dos pasos, igual que en "Mis BPMN".
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
        onDelete(id);
    }

    return (
        <Sidebar>
            <SidebarHeader className="p-2">
                <Button
                    variant="outline"
                    className="w-full justify-start gap-2"
                    onClick={startNewChat}
                >
                    <PlusIcon />
                    Nuevo chat
                </Button>
            </SidebarHeader>

            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>Chats</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {sessions.length === 0 ? (
                                <li className="px-2 py-6 text-center text-xs text-muted-foreground">
                                    No hay chats todavía.
                                </li>
                            ) : (
                                sessions.map((session) => (
                                    <SidebarMenuItem key={session.id}>
                                        <SidebarMenuButton
                                            isActive={session.id === activeId}
                                            tooltip={session.title}
                                            onClick={() => select(session.id)}
                                        >
                                            <MessageSquareIcon />
                                            <span className="truncate">
                                                {session.title}
                                            </span>
                                        </SidebarMenuButton>
                                        <SidebarMenuAction
                                            showOnHover
                                            aria-label="Eliminar chat"
                                            title={
                                                deleteArmId === session.id
                                                    ? "Confirmar eliminación"
                                                    : "Eliminar"
                                            }
                                            onClick={() =>
                                                handleDelete(session.id)
                                            }
                                            className={
                                                deleteArmId === session.id
                                                    ? "bg-destructive/20 text-destructive hover:bg-destructive/30 hover:text-destructive"
                                                    : undefined
                                            }
                                        >
                                            <TrashIcon />
                                        </SidebarMenuAction>
                                    </SidebarMenuItem>
                                ))
                            )}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            <SidebarFooter />
        </Sidebar>
    );
}
