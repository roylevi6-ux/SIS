import type { Metadata } from 'next';
import { DM_Sans, DM_Mono } from 'next/font/google';
import './globals.css';

import { Providers } from '@/components/providers';
import { AuthGuard } from '@/components/auth-guard';
import { ErrorBoundary } from '@/components/error-boundary';
import { DesktopSidebar, MobileSidebar } from '@/components/sidebar';

const dmSans = DM_Sans({
  variable: '--font-dm-sans',
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500', '600', '700'],
});

const dmMono = DM_Mono({
  variable: '--font-dm-mono',
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500'],
});

export const metadata: Metadata = {
  title: 'SIS — Sales Intelligence System',
  description: 'AI-powered sales pipeline intelligence',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${dmSans.variable} ${dmMono.variable} antialiased`}
      >
        <Providers>
          <AuthGuard>
            {/* Desktop fixed sidebar */}
            <DesktopSidebar />

            {/* Mobile Sheet sidebar + hamburger trigger */}
            <MobileSidebar />

            {/* Main content area: offset by sidebar width on desktop */}
            <ErrorBoundary>
              <main className="min-h-screen lg:ml-64">
                {/* Top padding on mobile to clear the hamburger button */}
                <div className="pt-16 lg:pt-0">{children}</div>
              </main>
            </ErrorBoundary>
          </AuthGuard>
        </Providers>
      </body>
    </html>
  );
}
