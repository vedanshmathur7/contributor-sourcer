"use client";
import * as React from "react";
import * as D from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Dialog = D.Root;
export const DialogTrigger = D.Trigger;
export const DialogClose = D.Close;

function Overlay() {
  return <D.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />;
}

export function DialogContent({ className, children, title, description }: { className?: string; children: React.ReactNode; title: string; description?: string }) {
  return (
    <D.Portal>
      <Overlay />
      <D.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-popover p-6 shadow-2xl data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
          className,
        )}
      >
        <D.Title className="text-base font-semibold">{title}</D.Title>
        {description && <D.Description className="mt-1 text-sm text-muted-foreground">{description}</D.Description>}
        <div className="mt-4">{children}</div>
        <D.Close className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground" aria-label="Close">
          <X className="h-4 w-4" />
        </D.Close>
      </D.Content>
    </D.Portal>
  );
}

export function Sheet({ open, onOpenChange, children, title, description }: { open: boolean; onOpenChange: (o: boolean) => void; children: React.ReactNode; title: string; description?: string }) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <Overlay />
        <D.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l bg-background shadow-2xl data-[state=open]:animate-in data-[state=open]:slide-in-from-right data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right duration-300">
          <D.Title className="sr-only">{title}</D.Title>
          {description && <D.Description className="sr-only">{description}</D.Description>}
          <D.Close className="absolute right-4 top-4 z-10 rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" aria-label="Close">
            <X className="h-4 w-4" />
          </D.Close>
          <div className="scrollbar-thin flex-1 overflow-y-auto">{children}</div>
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}
