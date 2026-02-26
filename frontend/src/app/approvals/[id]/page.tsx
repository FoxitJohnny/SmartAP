'use client';

import React, { useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge } from '@/components/invoices/status-badge';
import { MatchingResultCard } from '@/components/invoices/matching-result-card';
import { ApprovalActionDialog } from '@/components/approvals/approval-action-dialog';
import { useInvoice, useInvoiceMatchingResult } from '@/lib/api/invoices';
import { usePerformApprovalAction } from '@/lib/api/approvals';
import { usePurchaseOrder } from '@/lib/api/purchase-orders';
import { format } from 'date-fns';
import { toast } from 'sonner';
import {
  CheckCircle,
  Eye,
  EyeOff,
  MessageSquare,
  ArrowUpCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

function getApiOrigin() {
  const api = process.env.NEXT_PUBLIC_API_URL;
  if (!api) return 'http://localhost:8000';
  return api.replace('/api/v1', '');
}

function withPdfViewerParams(url: string) {
  return `${url}#toolbar=1&navpanes=0&scrollbar=1`;
}

function getInvoicePdfUrl(invoiceId: string, invoiceFilePath?: string | null) {
  const origin = getApiOrigin();
  const path = invoiceFilePath || `/api/v1/invoices/${invoiceId}/pdf`;
  return withPdfViewerParams(`${origin}${path}`);
}

function getPurchaseOrderPdfUrl(poId: string) {
  const origin = getApiOrigin();
  return withPdfViewerParams(`${origin}/api/v1/purchase-orders/${encodeURIComponent(poId)}/pdf`);
}

export default function ApprovalReviewPage() {
  const router = useRouter();
  const params = useParams();
  const invoiceId = String(params?.id || '');

  const [showInvoicePDF, setShowInvoicePDF] = useState(true);
  const [showPoPDF, setShowPoPDF] = useState(true);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalActionType, setApprovalActionType] = useState<
    'APPROVE' | 'REJECT' | 'ESCALATE' | 'REQUEST_CHANGES'
  >('APPROVE');

  const invoiceQuery = useInvoice(invoiceId);
  const matchingQuery = useInvoiceMatchingResult(invoiceId);
  const performActionMutation = usePerformApprovalAction();

  const invoice = invoiceQuery.data;
  const matchingResult = matchingQuery.data;

  // Backend PO endpoints key off `po_number`, so prefer `po_number` and fall back to `po_id` only if needed.
  const poLookupId = useMemo(() => {
    if (!matchingResult) return '';
    return (matchingResult.po_number || matchingResult.po_id || '').toString();
  }, [matchingResult]);

  const poQuery = usePurchaseOrder(poLookupId, !!poLookupId);

  const canTakeAction = useMemo(() => {
    if (!invoice) return false;
    // Actions are meaningful when an invoice has entered a human-review stage.
    return (
      invoice.status === 'PENDING_APPROVAL' ||
      invoice.status === 'RISK_REVIEW' ||
      !!matchingResult?.requires_approval ||
      !!invoice.risk_level
    );
  }, [invoice, matchingResult]);

  const handleApprovalAction = (action: 'APPROVE' | 'REJECT' | 'ESCALATE' | 'REQUEST_CHANGES') => {
    setApprovalActionType(action);
    setShowApprovalDialog(true);
  };

  const handleApprovalConfirm = async (data: { comment?: string; reason?: string; assignTo?: string }) => {
    try {
      await performActionMutation.mutateAsync({
        invoiceId,
        action: {
          action: approvalActionType,
          comment: data.comment,
          reason: data.reason,
          assignTo: data.assignTo,
        },
      });
      toast.success(`Action ${approvalActionType} recorded`);
      setShowApprovalDialog(false);
      router.push('/approvals');
    } catch {
      toast.error('Failed to perform approval action');
    }
  };

  if (invoiceQuery.isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (invoiceQuery.error || !invoice) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
          <p className="text-lg font-medium">Failed to load invoice</p>
          <Button className="mt-4" onClick={() => router.push('/approvals')}>
            Back to Approval Queue
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Button variant="ghost" size="sm" onClick={() => router.push('/approvals')}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </Button>
            </div>
            <h2 className="text-3xl font-bold tracking-tight">Approval Review</h2>
            <p className="text-muted-foreground">
              Invoice {invoice.invoice_number || 'N/A'} · {invoice.vendor_name || 'Unknown Vendor'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => setShowInvoicePDF(!showInvoicePDF)}
              className="gap-2"
            >
              {showInvoicePDF ? (
                <>
                  <EyeOff className="h-4 w-4" />
                  Hide Invoice
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4" />
                  Show Invoice
                </>
              )}
            </Button>

            <Button
              variant="outline"
              onClick={() => setShowPoPDF(!showPoPDF)}
              className="gap-2"
              disabled={!poLookupId}
              title={!poLookupId ? 'No matched PO to show' : undefined}
            >
              {showPoPDF ? (
                <>
                  <EyeOff className="h-4 w-4" />
                  Hide PO
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4" />
                  Show PO
                </>
              )}
            </Button>

            {canTakeAction && (
              <>
                <Button
                  variant="outline"
                  onClick={() => handleApprovalAction('REQUEST_CHANGES')}
                  disabled={performActionMutation.isPending}
                  className="gap-2"
                >
                  <MessageSquare className="h-4 w-4" />
                  Request Changes
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleApprovalAction('ESCALATE')}
                  disabled={performActionMutation.isPending}
                  className="gap-2"
                >
                  <ArrowUpCircle className="h-4 w-4" />
                  Escalate
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleApprovalAction('REJECT')}
                  disabled={performActionMutation.isPending}
                  className="gap-2"
                >
                  <XCircle className="h-4 w-4" />
                  Reject
                </Button>
                <Button
                  onClick={() => handleApprovalAction('APPROVE')}
                  disabled={performActionMutation.isPending}
                  className="gap-2"
                >
                  <CheckCircle className="h-4 w-4" />
                  Approve
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Approval Action Dialog */}
        <ApprovalActionDialog
          open={showApprovalDialog}
          onOpenChange={setShowApprovalDialog}
          actionType={approvalActionType}
          invoiceNumber={invoice.invoice_number}
          onConfirm={handleApprovalConfirm}
          isLoading={performActionMutation.isPending}
        />

        {/* Top summary */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
            </CardHeader>
            <CardContent>
              <StatusBadge status={invoice.status} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Total Amount</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${invoice.total_amount?.toFixed(2) || '0.00'}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Invoice Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg">
                {invoice.invoice_date ? format(new Date(invoice.invoice_date), 'MMM d, yyyy') : 'N/A'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Matched PO</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-medium">{matchingResult?.po_number || '—'}</div>
            </CardContent>
          </Card>
        </div>

        {/* Review workspace */}
        <div className="grid gap-6 xl:grid-cols-3">
          {/* Invoice PDF */}
          {showInvoicePDF ? (
            <Card className="overflow-hidden xl:col-span-1">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Invoice PDF</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <iframe
                  title={`invoice-${invoice.invoice_number || invoiceId}.pdf`}
                  src={getInvoicePdfUrl(invoiceId, invoice.file_path)}
                  className="w-full h-[75vh] border-0"
                />
              </CardContent>
            </Card>
          ) : null}

          {/* PO PDF */}
          {showPoPDF ? (
            <Card className="overflow-hidden xl:col-span-1">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Purchase Order PDF</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {!poLookupId ? (
                  <div className="p-4 text-sm text-muted-foreground">No matched PO available.</div>
                ) : (
                  <iframe
                    title={`po-${poLookupId}.pdf`}
                    src={getPurchaseOrderPdfUrl(poLookupId)}
                    className="w-full h-[75vh] border-0"
                  />
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* AI evaluation + details */}
          <div className="space-y-6 xl:col-span-1">
            {/* Matching summary */}
            {!matchingResult ? (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">PO Matching</CardTitle>
                </CardHeader>
                <CardContent>
                  {matchingQuery.isLoading ? (
                    <p className="text-sm text-muted-foreground">Loading matching result...</p>
                  ) : matchingQuery.error ? (
                    <p className="text-sm text-muted-foreground">Unable to load matching result.</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">No matching result available.</p>
                  )}
                </CardContent>
              </Card>
            ) : (
              <MatchingResultCard result={matchingResult} />
            )}

            {/* PO details */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Purchase Order</CardTitle>
              </CardHeader>
              <CardContent>
                {!poLookupId ? (
                  <p className="text-sm text-muted-foreground">No PO matched.</p>
                ) : poQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading purchase order...</p>
                ) : poQuery.error || !poQuery.data ? (
                  <p className="text-sm text-muted-foreground">Unable to load purchase order details.</p>
                ) : (
                  <div className="space-y-3">
                    <div className="grid gap-2 md:grid-cols-2">
                      <div>
                        <div className="text-xs text-muted-foreground">PO Number</div>
                        <div className="font-medium">{poQuery.data.po_number}</div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground">Vendor</div>
                        <div className="font-medium">{poQuery.data.vendor_name}</div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground">Total</div>
                        <div className="font-medium">${Number(poQuery.data.total_amount || 0).toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground">Status</div>
                        <div className="font-medium">{poQuery.data.status}</div>
                      </div>
                    </div>

                    {poQuery.data.line_items?.length ? (
                      <div className="border rounded-md overflow-hidden">
                        <table className="w-full text-sm">
                          <thead className="border-b bg-muted/50">
                            <tr className="text-left text-muted-foreground">
                              <th className="p-2">Line</th>
                              <th className="p-2">Description</th>
                              <th className="p-2 text-right">Qty</th>
                              <th className="p-2 text-right">Unit</th>
                              <th className="p-2 text-right">Total</th>
                            </tr>
                          </thead>
                          <tbody>
                            {poQuery.data.line_items.map((li) => (
                              <tr key={li.id} className="border-b last:border-b-0">
                                <td className="p-2">{li.line_number}</td>
                                <td className="p-2">{li.description}</td>
                                <td className="p-2 text-right">{Number(li.quantity || 0)}</td>
                                <td className="p-2 text-right">${Number(li.unit_price || 0).toFixed(2)}</td>
                                <td className="p-2 text-right">${Number(li.total_amount || 0).toFixed(2)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No PO line items.</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
