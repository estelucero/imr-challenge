"use client";

import { Chat } from "@/components/chat/chat";

export function Workspace() {
    return (
        <div className="flex h-full min-h-0 w-full overflow-hidden">
            <div className="flex h-full min-h-0 flex-1 flex-col">
                <Chat />
            </div>
        </div>
    );
}
