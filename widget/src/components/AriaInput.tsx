import { useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";

export function AriaInput({
  onSend,
  disabled,
  accent,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
  accent: string;
}) {
  const [value, setValue] = useState("");

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={submit} className="flex items-end gap-2 border-t border-white/10 px-3 py-2.5">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        placeholder="Type your message…"
        className="max-h-24 flex-1 resize-none rounded-2xl border border-white/10 bg-white/5 px-3.5 py-2 text-sm text-parchment placeholder:text-dust focus:outline-none"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink disabled:cursor-not-allowed disabled:opacity-40"
        style={{ backgroundColor: accent }}
      >
        <ArrowUp size={16} strokeWidth={2.5} />
      </button>
    </form>
  );
}
