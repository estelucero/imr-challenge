import { AppSidebar } from "@/components/chat/sidebar";
import {
    SidebarInset,
    SidebarProvider,
    SidebarTrigger,
} from "@/components/ui/sidebar";
import { Workspace } from "@/components/workspace";

export default function Home() {
    return (
        <SidebarProvider className="h-dvh overflow-hidden">
            <AppSidebar />

            <SidebarInset className="min-w-0 overflow-hidden">
                <header className="flex h-12 shrink-0 items-center gap-2 border-b px-2">
                    <SidebarTrigger />
                </header>

                <div className="min-h-0 flex-1">
                    <Workspace />
                </div>
            </SidebarInset>
        </SidebarProvider>
    );
}
