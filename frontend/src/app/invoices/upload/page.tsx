'use client';

import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { InvoiceUpload } from '@/components/invoices/invoice-upload';

export default function InvoiceUploadPage() {
  const router = useRouter();

  const handleUploadComplete = (invoiceId: string) => {
    // Optionally redirect to the invoice detail page
    // router.push(`/invoices/${invoiceId}`);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/invoices')}
            >
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
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              Back to Invoices
            </Button>
          </div>
          <h2 className="text-3xl font-bold tracking-tight">Upload Invoices</h2>
          <p className="text-muted-foreground">
            Upload invoice documents for processing and OCR extraction
          </p>
        </div>

        {/* Upload Component */}
        <InvoiceUpload onUploadComplete={handleUploadComplete} />
      </div>
    </DashboardLayout>
  );
}
