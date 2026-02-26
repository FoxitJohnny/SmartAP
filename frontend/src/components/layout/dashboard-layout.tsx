'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';
import { useUIStore } from '@/stores/uiStore';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const pathname = usePathname();

  // Close sidebar on mobile when route changes or on initial load
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setSidebarOpen(false);
      }
    };
    
    // Close on mount if mobile
    handleResize();
    
    // Close on resize to mobile
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [setSidebarOpen]);

  // Close sidebar on mobile when navigating
  useEffect(() => {
    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, [pathname, setSidebarOpen]);

  return (
    <ProtectedRoute>
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden lg:pl-64">
          <Header />
          <main className="flex-1 overflow-y-auto bg-muted/40 p-4 sm:p-6">
            {children}
          </main>
        </div>

        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </div>
    </ProtectedRoute>
  );
}
