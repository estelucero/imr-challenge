import * as React from "react";
import { cn } from "cn";

function Loader({ className, ...props }: React.ComponentProps<"span">) {
    return (
        <span
            role="status"
            aria-label="Generando respuesta"
            className={cn("inline-flex items-center gap-1", className)}
            {...props}
        >
            <span className="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
            <span className="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
            <span className="size-1.5 animate-bounce rounded-full bg-current" />
        </span>
    );
}

export { Loader };
