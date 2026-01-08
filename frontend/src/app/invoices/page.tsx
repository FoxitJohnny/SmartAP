'use client';

import { useState } from 'react';
import Link from 'next/link';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { InvoiceList } from '@/components/invoices/invoice-list';
import { InvoiceFilters } from '@/components/invoices/invoice-filters';
import type { InvoiceFilters as IInvoiceFilters } from '@/types';

export default function InvoicesPage() {
  const [filters, setFilters] = useState<IInvoiceFilters>({});

  const handleClearFilters = () => {
    setFilters({});
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Invoices</h2>
            <p className="text-muted-foreground">
              Manage and process your invoices
            </p>
          </div>
          <Link href="/invoices/upload">
            <Button>
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              Upload Invoice
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <InvoiceFilters
          filters={filters}
          onFiltersChange={setFilters}
          onClear={handleClearFilters}
        />

        {/* Invoice List */}
        <InvoiceList filters={filters} />
      </div>
    </DashboardLayout>
  );
}
