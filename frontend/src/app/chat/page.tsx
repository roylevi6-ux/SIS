'use client';

import { useState, useRef, useEffect } from 'react';
import { useChatQuery } from '@/lib/hooks/use-chat';
import { ChatMessage } from '@/components/chat-message';
import { ChatInput } from '@/components/chat-input';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const WELCOME_MESSAGE: Message = {
  role: 'assistant',
  content:
    'Welcome! Ask me anything about your pipeline deals, forecast, or team performance. I have context from all your analyzed accounts.',
};

const SUGGESTED_QUERIES = [
  'How is my pipeline looking overall?',
  'Which deals are most at risk?',
  'What should I focus on this week?',
  'Show me forecast divergences',
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const { mutateAsync, isPending } = useChatQuery();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isPending]);

  async function handleSend(text?: string) {
    const content = (text ?? input).trim();
    if (!content || isPending) return;

    const userMessage: Message = { role: 'user', content };

    // Build history from current messages (exclude welcome for cleaner context)
    const history = messages
      .filter((m) => !(m.role === 'assistant' && m === WELCOME_MESSAGE))
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      const result = await mutateAsync({ message: content, history });
      const assistantMessage: Message = {
        role: 'assistant',
        content: result.response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage: Message = {
        role: 'assistant',
        content:
          'Sorry, I encountered an error processing your request. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  }

  function handleSuggestion(query: string) {
    handleSend(query);
  }

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)] lg:h-screen p-0">
      {/* Header */}
      <div className="shrink-0 px-4 py-4 sm:px-6 border-b border-border bg-card">
        <h1 className="text-xl font-semibold text-foreground">AI Assistant</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Ask questions about your pipeline deals
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6 space-y-4">
        {messages.map((message, index) => (
          <ChatMessage key={index} role={message.role} content={message.content} />
        ))}

        {/* Loading indicator */}
        {isPending && (
          <div className="flex items-start gap-2">
            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs font-medium text-muted-foreground px-1">
                AI Assistant
              </span>
              <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex gap-1 items-center">
                  <span
                    className="size-2 rounded-full bg-muted-foreground/50 animate-bounce"
                    style={{ animationDelay: '0ms' }}
                  />
                  <span
                    className="size-2 rounded-full bg-muted-foreground/50 animate-bounce"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="size-2 rounded-full bg-muted-foreground/50 animate-bounce"
                    style={{ animationDelay: '300ms' }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-border bg-card px-4 py-3 sm:px-6 sm:py-4">
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={() => handleSend()}
          disabled={isPending}
        />

        {/* Suggested queries */}
        <div className="flex flex-wrap gap-2 mt-3">
          {SUGGESTED_QUERIES.map((query) => (
            <button
              key={query}
              type="button"
              onClick={() => handleSuggestion(query)}
              disabled={isPending}
              className="text-xs px-3 py-1.5 rounded-full border border-border bg-background
                         text-muted-foreground hover:text-foreground hover:bg-muted
                         transition-colors disabled:pointer-events-none disabled:opacity-50
                         min-h-[32px]"
            >
              {query}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
