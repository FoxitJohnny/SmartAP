/**
 * Application Providers
 * 
 * Wraps the application with necessary providers (React Query, Theme, etc.)
 */

'use client';

import { useState, useEffect } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider } from 'next-themes';
import { queryClient } from '@/lib/api/query-client';
import { Toaster } from '@/components/ui/sonner';

export function Providers({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        {children}
        {mounted && <Toaster />}
        {mounted && <ReactQueryDevtools initialIsOpen={false} />}
      </QueryClientProvider>
    </ThemeProvider>
  );
}
