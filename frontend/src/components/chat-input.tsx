'use client';

import { useRef, KeyboardEvent, ChangeEvent } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = 'Ask about your pipeline...',
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    onChange(e.target.value);
    // Auto-grow: reset height then set to scrollHeight capped at 4 rows (~96px)
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 96)}px`;
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) {
        onSubmit();
        // Reset height after send
        if (textareaRef.current) {
          textareaRef.current.style.height = 'auto';
        }
      }
    }
  }

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className={cn(
          'flex-1 resize-none rounded-xl border border-input bg-background px-4 py-3',
          'text-base placeholder:text-muted-foreground',
          'focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring',
          'transition-[color,box-shadow] disabled:cursor-not-allowed disabled:opacity-50',
          'min-h-[44px] max-h-24 overflow-y-auto',
          'shadow-xs',
        )}
        style={{ height: 'auto' }}
      />
      <Button
        type="button"
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        size="icon-lg"
        className="shrink-0 rounded-xl"
        aria-label="Send message"
      >
        <Send className="size-5" />
      </Button>
    </div>
  );
}
