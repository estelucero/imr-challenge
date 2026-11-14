"use client";

import * as React from "react";

import { BpmnPanel } from "@/components/bpmn/bpmn-panel";
import { Chat } from "@/components/chat/chat";

export function Workspace() {
    const [diagramXml, setDiagramXml] = React.useState<string | null>(null);

    return (
        <div className="flex h-full min-h-0 w-full overflow-hidden">
            <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
                <Chat onDiagram={setDiagramXml} />
            </div>

            {diagramXml && (
                <section className="hidden h-full min-h-0 w-[45%] max-w-3xl shrink-0 flex-col border-l md:flex">
                    <BpmnPanel xml={diagramXml} />
                </section>
            )}
        </div>
    );
}
