'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { AuthProvider } from '@/lib/auth';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
      })
  );

  // Clear all cached queries on logout so stale errors don't persist
  const handleLogout = useCallback(() => {
    queryClient.clear();
  }, [queryClient]);

  return (
    <AuthProvider onLogout={handleLogout}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </AuthProvider>
  );
}
