'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge, RiskBadge } from '@/components/invoices/status-badge';
import { PDFViewer } from '@/components/invoices/pdf-viewer';
import { PDFAnnotationToolbar } from '@/components/invoices/pdf-annotation-toolbar';
import { InvoiceFieldOverlay } from '@/components/invoices/invoice-field-overlay';
import { ApprovalWorkflowVisualizer } from '@/components/approvals/approval-workflow-visualizer';
import { ApprovalHistoryTimeline } from '@/components/approvals/approval-history-timeline';
import { ApprovalActionDialog } from '@/components/approvals/approval-action-dialog';
import { useInvoice, useApproveInvoice, useRejectInvoice, useRetryOCR } from '@/lib/api/invoices';
import {
  useApprovalWorkflow,
  useApprovalHistory,
  usePerformApprovalAction,
} from '@/lib/api/approvals';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { FileText, Eye, EyeOff, CheckCircle, XCircle, ArrowUpCircle, MessageSquare } from 'lucide-react';
import type { Annotation } from '@/types/foxit';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export default function InvoiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const invoiceId = params?.id as string;
  const [showPDFViewer, setShowPDFViewer] = useState(true);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalActionType, setApprovalActionType] = useState<
    'APPROVE' | 'REJECT' | 'ESCALATE' | 'REQUEST_CHANGES'
  >('APPROVE');

  const { data: invoice, isLoading, error } = useInvoice(invoiceId);
  const { data: workflow } = useApprovalWorkflow(invoiceId);
  const { data: history } = useApprovalHistory(invoiceId);
  const approveMutation = useApproveInvoice();
  const rejectMutation = useRejectInvoice();
  const retryOCRMutation = useRetryOCR();
  const performActionMutation = usePerformApprovalAction();

  const handleApprove = async () => {
    try {
      await approveMutation.mutateAsync({ id: invoiceId });
      toast.success('Invoice approved successfully');
    } catch (error) {
      toast.error('Failed to approve invoice');
    }
  };

  const handleReject = async () => {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;

    try {
      await rejectMutation.mutateAsync({ id: invoiceId, reason });
      toast.success('Invoice rejected');
    } catch (error) {
      toast.error('Failed to reject invoice');
    }
  };

  const handleRetryOCR = async () => {
    try {
      await retryOCRMutation.mutateAsync(invoiceId);
      toast.success('OCR processing restarted');
    } catch (error) {
      toast.error('Failed to retry OCR');
    }
  };

  const handleAnnotationCreate = (annotation: Partial<Annotation>) => {
    const newAnnotation: Annotation = {
      id: `ann-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: annotation.type || 'note',
      pageIndex: annotation.pageIndex || 0,
      content: annotation.content,
      color: annotation.color,
      author: annotation.author,
      createdDate: annotation.createdDate,
    };
    setAnnotations([...annotations, newAnnotation]);
    toast.success('Annotation added');
  };

  const handleAnnotationDelete = (annotationId: string) => {
    setAnnotations(annotations.filter((a) => a.id !== annotationId));
    toast.success('Annotation deleted');
  };

  const handleFieldClick = (fieldName: string, currentValue: any) => {
    const newValue = prompt(`Edit ${fieldName}:`, currentValue);
    if (newValue && newValue !== currentValue) {
      // TODO: Implement field update API
      toast.success(`${fieldName} will be updated to: ${newValue}`);
    }
  };

  const handleApprovalAction = (actionType: 'APPROVE' | 'REJECT' | 'ESCALATE' | 'REQUEST_CHANGES') => {
    setApprovalActionType(actionType);
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
      toast.success(`Invoice ${approvalActionType.toLowerCase()} successfully`);
      setShowApprovalDialog(false);
    } catch (error) {
      toast.error(`Failed to ${approvalActionType.toLowerCase()} invoice`);
    }
  };

  const getPDFUrl = () => {
    // Construct PDF URL from file path
    if (invoice?.file_path) {
      return `${process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '')}${invoice.file_path}`;
    }
    return '';
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !invoice) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <svg
            className="w-12 h-12 text-red-500 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-lg font-medium">Invoice not found</p>
          <Button className="mt-4" onClick={() => router.push('/invoices')}>
            Back to Invoices
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
                Back
              </Button>
            </div>
            <h2 className="text-3xl font-bold tracking-tight">
              Invoice {invoice.invoice_number || 'N/A'}
            </h2>
            <p className="text-muted-foreground">
              {invoice.vendor_name || 'Unknown Vendor'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => setShowPDFViewer(!showPDFViewer)}
              className="gap-2"
            >
              {showPDFViewer ? (
                <>
                  <EyeOff className="h-4 w-4" />
                  Hide PDF
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4" />
                  Show PDF
                </>
              )}
            </Button>
            {invoice.status === 'EXTRACTED' && (
              <Button variant="outline" onClick={handleRetryOCR} disabled={retryOCRMutation.isPending}>
                Retry OCR
              </Button>
            )}
            {invoice.status === 'RISK_REVIEW' && (
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

        {/* Overview Cards */}
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
              <div className="text-2xl font-bold">
                ${invoice.total_amount?.toFixed(2) || '0.00'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Invoice Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg">
                {invoice.invoice_date
                  ? format(new Date(invoice.invoice_date), 'MMM d, yyyy')
                  : 'N/A'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Due Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg">
                {invoice.due_date
                  ? format(new Date(invoice.due_date), 'MMM d, yyyy')
                  : 'N/A'}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* PDF Viewer Section */}
        {showPDFViewer && getPDFUrl() && (
          <div className="grid gap-6 lg:grid-cols-3">
            {/* PDF Viewer - Takes 2 columns */}
            <div className="lg:col-span-2">
              <PDFViewer
                documentUrl={getPDFUrl()}
                fileName={`invoice-${invoice.invoice_number || invoiceId}.pdf`}
                onDocumentLoad={() => toast.success('PDF loaded successfully')}
                onDocumentError={(error) => toast.error(`Failed to load PDF: ${error.message}`)}
              />
            </div>

            {/* Side Panel - Takes 1 column */}
            <div className="space-y-4">
              {/* Field Overlay */}
              <InvoiceFieldOverlay invoice={invoice} onFieldClick={handleFieldClick} />

              {/* Annotation Toolbar */}
              <PDFAnnotationToolbar
                onAnnotationCreate={handleAnnotationCreate}
                onAnnotationDelete={handleAnnotationDelete}
                annotations={annotations}
                currentPage={1}
              />
            </div>
          </div>
        )}

        {!showPDFViewer && (
          <Card className="p-8">
            <div className="flex flex-col items-center justify-center text-center space-y-4">
              <FileText className="h-16 w-16 text-muted-foreground" />
              <div>
                <h3 className="font-semibold text-lg mb-2">PDF Viewer Hidden</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Click "Show PDF" to view the invoice document
                </p>
                <Button onClick={() => setShowPDFViewer(true)}>
                  <Eye className="h-4 w-4 mr-2" />
                  Show PDF
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Overview Cards */}
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
              <div className="text-2xl font-bold">
                ${invoice.total_amount?.toFixed(2) || '0.00'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Invoice Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg">
                {invoice.invoice_date
                  ? format(new Date(invoice.invoice_date), 'MMM d, yyyy')
                  : 'N/A'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Due Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg">
                {invoice.due_date
                  ? format(new Date(invoice.due_date), 'MMM d, yyyy')
                  : 'N/A'}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Risk Flags */}
        {invoice.risk_flags && invoice.risk_flags.length > 0 && (
          <Card className="border-red-200 dark:border-red-900">
            <CardHeader>
              <CardTitle className="text-red-600 dark:text-red-400">
                Risk Flags ({invoice.risk_flags.length})
              </CardTitle>
              <CardDescription>Issues detected that require attention</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {invoice.risk_flags.map((flag, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-950/20"
                  >
                    <svg
                      className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <RiskBadge level={flag.severity} />
                        <span className="font-medium text-sm">{flag.type}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{flag.description}</p>
                      {flag.details && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Details: {JSON.stringify(flag.details)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Invoice Details */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Invoice Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="text-sm text-muted-foreground">Invoice Number:</div>
                <div className="text-sm font-medium">{invoice.invoice_number || 'N/A'}</div>

                <div className="text-sm text-muted-foreground">PO Number:</div>
                <div className="text-sm font-medium">{invoice.po_number || 'N/A'}</div>

                <div className="text-sm text-muted-foreground">Currency:</div>
                <div className="text-sm font-medium">{invoice.currency || 'USD'}</div>

                <div className="text-sm text-muted-foreground">Tax Amount:</div>
                <div className="text-sm font-medium">
                  ${invoice.tax_amount?.toFixed(2) || '0.00'}
                </div>

                <div className="text-sm text-muted-foreground">Subtotal:</div>
                <div className="text-sm font-medium">
                  ${invoice.subtotal?.toFixed(2) || '0.00'}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Vendor Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="text-sm text-muted-foreground">Vendor Name:</div>
                <div className="text-sm font-medium">{invoice.vendor_name || 'N/A'}</div>

                <div className="text-sm text-muted-foreground">Vendor ID:</div>
                <div className="text-sm font-medium">{invoice.vendor_id || 'N/A'}</div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Line Items */}
        {invoice.line_items && invoice.line_items.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Line Items</CardTitle>
              <CardDescription>
                {invoice.line_items.length} item(s)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Quantity</TableHead>
                    <TableHead className="text-right">Unit Price</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoice.line_items.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>{item.description || 'N/A'}</TableCell>
                      <TableCell className="text-right">{item.quantity || 0}</TableCell>
                      <TableCell className="text-right">
                        ${item.unit_price?.toFixed(2) || '0.00'}
                      </TableCell>
                      <TableCell className="text-right">
                        ${item.line_total?.toFixed(2) || '0.00'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* OCR Data */}
        {invoice.ocr_data && (
          <Card>
            <CardHeader>
              <CardTitle>OCR Extracted Data</CardTitle>
              <CardDescription>Raw data extracted from the invoice</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto">
                {JSON.stringify(invoice.ocr_data, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Approval Workflow & History */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Approval Workflow */}
          {workflow && <ApprovalWorkflowVisualizer workflow={workflow} />}

          {/* Approval History */}
          {history && <ApprovalHistoryTimeline history={history} />}
        </div>
      </div>
    </DashboardLayout>
  );
}
