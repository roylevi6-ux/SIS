import { cn } from '@/lib/utils';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
  const isUser = role === 'user';

  return (
    <div
      className={cn(
        'flex flex-col gap-1',
        isUser ? 'items-end' : 'items-start',
      )}
    >
      <span className="text-xs font-medium text-muted-foreground px-1">
        {isUser ? 'You' : 'AI Assistant'}
      </span>
      <div
        className={cn(
          'max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words whitespace-pre-wrap',
          isUser
            ? 'bg-primary text-primary-foreground rounded-br-sm'
            : 'bg-muted text-foreground rounded-bl-sm',
        )}
      >
        {content}
      </div>
    </div>
  );
}
