import type { ButtonHTMLAttributes } from "react";
import { clsx } from "../../utils/clsx";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
}

export function Button({ variant = "primary", size = "md", className, ...props }: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        size === "md" ? "px-5 py-2.5 text-sm" : "px-3.5 py-1.5 text-xs",
        variant === "primary" && "bg-brass text-ink hover:bg-brass-light",
        variant === "secondary" && "bg-ink-soft border border-ink-border text-parchment hover:border-brass/50",
        variant === "ghost" && "text-dust hover:text-parchment",
        variant === "danger" && "bg-red-500/10 border border-red-500/30 text-red-300 hover:bg-red-500/20",
        className
      )}
      {...props}
    />
  );
}
