"use client";

import * as React from "react";
import { ChevronDownIcon } from "lucide-react";

import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuLabel,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { InputGroupButton } from "@/components/ui/input-group";
import { type ChatModel } from "@/lib/chat/models";

type ModelSelectorProps = {
    models: ChatModel[];
    value: ChatModel;
    onChange: (model: ChatModel) => void;
};

export function ModelSelector({ models, value, onChange }: ModelSelectorProps) {
    const [query, setQuery] = React.useState("");

    const normalizedQuery = query.trim().toLowerCase();
    const filtered = normalizedQuery
        ? models.filter(
              (m) =>
                  m.name.toLowerCase().includes(normalizedQuery) ||
                  m.vendor.toLowerCase().includes(normalizedQuery) ||
                  m.id.toLowerCase().includes(normalizedQuery),
          )
        : models;

    const openAiModels = filtered.filter((m) => m.provider === "openai");
    const openRouterModels = filtered.filter((m) => m.provider === "openrouter");

    function renderItems(items: ChatModel[]) {
        if (items.length === 0) return null;

        return (
            <DropdownMenuGroup>
                <DropdownMenuLabel>
                    {items[0].provider === "openai" ? "OpenAI" : "OpenRouter"}
                </DropdownMenuLabel>
                <DropdownMenuRadioGroup
                    value={value.provider + "/" + value.id}
                    onValueChange={(newValue) => {
                        const model = models.find(
                            (m) => m.provider + "/" + m.id === newValue,
                        );
                        if (model) onChange(model);
                    }}
                >
                    {items.map((model) => (
                        <DropdownMenuRadioItem
                            key={model.id}
                            value={model.provider + "/" + model.id}
                            closeOnClick
                            className="items-start py-2"
                        >
                            <div className="flex min-w-0 flex-col">
                                <span className="truncate">{model.name}</span>
                                <span className="truncate text-xs text-muted-foreground">
                                    {model.vendor}
                                </span>
                            </div>
                        </DropdownMenuRadioItem>
                    ))}
                </DropdownMenuRadioGroup>
            </DropdownMenuGroup>
        );
    }

    return (
        <DropdownMenu>
            <DropdownMenuTrigger
                render={
                    <InputGroupButton
                        variant="ghost"
                        size="sm"
                        aria-label="Seleccionar modelo"
                    >
                        <span className="max-w-40 truncate font-normal text-muted-foreground">
                            {value.name}
                        </span>
                        <ChevronDownIcon className="size-3.5 text-muted-foreground" />
                    </InputGroupButton>
                }
            />
            <DropdownMenuContent className="w-72" align="start">
                <div className="p-1">
                    <input
                        type="text"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Buscar modelo..."
                        className="h-7 w-full rounded-md border border-input bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                        onKeyDown={(event) => event.stopPropagation()}
                    />
                </div>
                <DropdownMenuSeparator />
                {openAiModels.length === 0 && openRouterModels.length === 0 ? (
                    <div className="px-2 py-3 text-center text-sm text-muted-foreground">
                        Sin resultados.
                    </div>
                ) : (
                    <>
                        {renderItems(openAiModels)}
                        {openAiModels.length > 0 &&
                            openRouterModels.length > 0 && (
                                <DropdownMenuSeparator />
                            )}
                        {renderItems(openRouterModels)}
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
