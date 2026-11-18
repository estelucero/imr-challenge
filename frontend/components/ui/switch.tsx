"use client";

import * as React from "react";
import { Switch as SwitchPrimitive } from "@base-ui/react/switch";

import { cn } from "@/lib/utils";

function Switch({
    className,
    children,
    ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
    return (
        <SwitchPrimitive.Root
            className={cn(
                "peer inline-flex h-[1.15rem] w-8 shrink-0 items-center rounded-full border border-transparent p-px text-xs font-medium shadow-xs transition-all outline-none data-checked:bg-primary data-unchecked:bg-input data-unchecked:data-disabled:cursor-not-allowed data-unchecked:data-disabled:opacity-50 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-1 data-checked:focus-visible:ring-primary/40 dark:data-unchecked:bg-input/80",
                className,
            )}
            {...props}
        >
            {children ?? (
                <SwitchPrimitive.Thumb
                    className={cn(
                        "pointer-events-none block size-4 rounded-full bg-background ring-0 transition-all data-checked:translate-x-[calc(100%-2px)] dark:data-checked:bg-primary-foreground dark:data-unchecked:bg-foreground",
                    )}
                />
            )}
        </SwitchPrimitive.Root>
    );
}

export { Switch };
