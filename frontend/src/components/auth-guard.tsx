'use client';

import { useAuth } from '@/lib/auth';
import LoginPage from '@/app/login/page';

/**
 * Gate that shows the login page when unauthenticated.
 * Wraps the entire app shell (sidebar + main content).
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return <>{children}</>;
}
