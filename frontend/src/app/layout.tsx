import type { Metadata } from 'next';
import { Inter, Geist_Mono } from 'next/font/google';
import './globals.css';

import { Providers } from '@/components/providers';
import { AuthGuard } from '@/components/auth-guard';
import { ErrorBoundary } from '@/components/error-boundary';
import { DesktopSidebar, MobileSidebar } from '@/components/sidebar';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
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
        className={`${inter.variable} ${geistMono.variable} antialiased`}
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
