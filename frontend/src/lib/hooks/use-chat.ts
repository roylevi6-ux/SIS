import { useMutation } from '@tanstack/react-query';
import { api } from '../api';

export function useChatQuery() {
  return useMutation({
    mutationFn: ({ message, history }: { message: string; history?: any[] }) =>
      api.chat.query(message, history),
  });
}
