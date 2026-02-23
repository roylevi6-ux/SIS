import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

import { Providers } from '@/components/providers';
import { AuthGuard } from '@/components/auth-guard';
import { DesktopSidebar, MobileSidebar } from '@/components/sidebar';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
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
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          <AuthGuard>
            {/* Desktop fixed sidebar */}
            <DesktopSidebar />

            {/* Mobile Sheet sidebar + hamburger trigger */}
            <MobileSidebar />

            {/* Main content area: offset by sidebar width on desktop */}
            <main className="min-h-screen lg:ml-64">
              {/* Top padding on mobile to clear the hamburger button */}
              <div className="pt-16 lg:pt-0">{children}</div>
            </main>
          </AuthGuard>
        </Providers>
      </body>
    </html>
  );
}
