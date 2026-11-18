"use client";

import * as React from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "cn";

import {
    CodeBlock,
    CodeBlockActions,
    CodeBlockContent,
    CodeBlockCopyButton,
    CodeBlockHeader,
    CodeBlockLine,
    CodeBlockTitle,
} from "@/components/ui/code-block";
import { useHighlightedCode } from "@/hooks/use-highlighted-code";

type CodeElementProps = {
    className?: string;
    children?: React.ReactNode;
};

function flattenText(node: React.ReactNode): string {
    if (node == null || typeof node === "boolean") return "";
    if (typeof node === "string" || typeof node === "number") {
        return String(node);
    }
    if (Array.isArray(node)) return node.map(flattenText).join("");
    if (React.isValidElement(node)) {
        return flattenText((node.props as CodeElementProps).children);
    }
    return "";
}

function MarkdownCodeBlock({ code, language }: { code: string; language?: string }) {
    const lines = useHighlightedCode(code, language ?? "");
    const title = language || "código";

    return (
        <CodeBlock size="sm">
            <CodeBlockHeader>
                <CodeBlockTitle>{title}</CodeBlockTitle>
                <CodeBlockActions>
                    <CodeBlockCopyButton value={code} />
                </CodeBlockActions>
            </CodeBlockHeader>
            <CodeBlockContent wrap>
                {lines.map((line, index) => (
                    <CodeBlockLine key={index}>{line}</CodeBlockLine>
                ))}
            </CodeBlockContent>
        </CodeBlock>
    );
}

const markdownComponents: Components = {
    h1: ({ className, ...props }) => (
        <h1 className={cn("mt-3 text-base font-semibold first:mt-0", className)} {...props} />
    ),
    h2: ({ className, ...props }) => (
        <h2 className={cn("mt-3 text-sm font-semibold first:mt-0", className)} {...props} />
    ),
    h3: ({ className, ...props }) => (
        <h3 className={cn("mt-2.5 text-sm font-semibold first:mt-0", className)} {...props} />
    ),
    h4: ({ className, ...props }) => (
        <h4 className={cn("mt-2.5 text-sm font-semibold first:mt-0", className)} {...props} />
    ),
    p: ({ className, ...props }) => (
        <p className={cn("mt-2 first:mt-0", className)} {...props} />
    ),
    ul: ({ className, ...props }) => (
        <ul
            className={cn(
                "mt-2 list-disc space-y-1 ps-5 first:mt-0 marker:text-muted-foreground [&_ol]:mt-1 [&_ul]:mt-1",
                className
            )}
            {...props}
        />
    ),
    ol: ({ className, ...props }) => (
        <ol
            className={cn(
                "mt-2 list-decimal space-y-1 ps-5 first:mt-0 marker:text-muted-foreground [&_ol]:mt-1 [&_ul]:mt-1",
                className
            )}
            {...props}
        />
    ),
    blockquote: ({ className, ...props }) => (
        <blockquote
            className={cn(
                "mt-2 border-s-2 border-border ps-3 text-muted-foreground first:mt-0",
                className
            )}
            {...props}
        />
    ),
    hr: ({ className, ...props }) => (
        <hr className={cn("my-3 border-border first:mt-0", className)} {...props} />
    ),
    a: ({ className, ...props }) => (
        <a
            className={cn("font-medium underline underline-offset-2", className)}
            target="_blank"
            rel="noreferrer"
            {...props}
        />
    ),
    table: ({ className, ...props }) => (
        <div className="mt-2 min-w-0 overflow-x-auto scrollbar-thin first:mt-0">
            <table className={cn("w-full border-collapse text-sm", className)} {...props} />
        </div>
    ),
    th: ({ className, ...props }) => (
        <th
            className={cn(
                "border-b border-border px-2 py-1 text-start font-semibold",
                className
            )}
            {...props}
        />
    ),
    td: ({ className, ...props }) => (
        <td className={cn("border-b border-border px-2 py-1 align-top", className)} {...props} />
    ),
    code: ({ className, children, ...props }) => (
        <code
            className={cn(
                "rounded-md bg-muted px-1 py-0.5 font-mono text-[0.85em]",
                className
            )}
            {...props}
        >
            {children}
        </code>
    ),
    pre: ({ children }) => {
        const child = React.Children.toArray(children)[0];

        if (!React.isValidElement(child)) {
            return <>{children}</>;
        }

        const { className, children: code } = child.props as CodeElementProps;
        const language = /language-([\w-]+)/.exec(className ?? "")?.[1];

        return <MarkdownCodeBlock code={flattenText(code)} language={language} />;
    },
};

function Markdown({ children, className }: { children: string; className?: string }) {
    return (
        <div className={cn("min-w-0 text-sm leading-relaxed wrap-break-word", className)}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {children}
            </ReactMarkdown>
        </div>
    );
}

export { Markdown };
