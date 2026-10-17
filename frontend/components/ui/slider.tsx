"use client";
import * as React from "react";
import * as S from "@radix-ui/react-slider";
import { cn } from "@/lib/utils";

export function Slider({ className, ...props }: React.ComponentProps<typeof S.Root>) {
  return (
    <S.Root className={cn("relative flex w-full touch-none select-none items-center py-2", className)} {...props}>
      <S.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-secondary">
        <S.Range className="absolute h-full bg-primary" />
      </S.Track>
      <S.Thumb
        aria-label={props["aria-label"]}
        className="block h-4 w-4 rounded-full border-2 border-primary bg-background shadow transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
    </S.Root>
  );
}
