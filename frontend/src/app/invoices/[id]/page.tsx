'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge, RiskBadge } from '@/components/invoices/status-badge';
import { PDFViewer } from '@/components/invoices/pdf-viewer';
import { InvoiceFieldOverlay } from '@/components/invoices/invoice-field-overlay';
import { useInvoice, useInvoiceMatchingResult, useRetryOCR } from '@/lib/api/invoices';
import { useInvoiceProcessingEvents } from '@/lib/api/processing';
import { useApprovalWorkflow, useApprovalHistory } from '@/lib/api/approvals';
import { MatchingResultCard } from '@/components/invoices/matching-result-card';
import { ProcessingEventsTable } from '@/components/processing/processing-events-table';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { FileText, Eye, EyeOff, ChevronDown, ChevronUp, History, ShieldAlert, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import type { RiskLevel, RiskAssessment, RiskFlag } from '@/types';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

// ============================================================================
// Risk Assessment Detail Card
// ============================================================================

const COMPONENT_WEIGHTS: Record<string, { label: string; weight: number; color: string }> = {
  duplicate: { label: 'Duplicate Detection', weight: 25, color: 'bg-red-500' },
  vendor: { label: 'Vendor Risk', weight: 20, color: 'bg-orange-500' },
  matching: { label: 'PO Matching', weight: 20, color: 'bg-blue-500' },
  price: { label: 'Price Anomaly', weight: 15, color: 'bg-yellow-500' },
  amount: { label: 'Amount Anomaly', weight: 10, color: 'bg-purple-500' },
  pattern: { label: 'Suspicious Patterns', weight: 10, color: 'bg-pink-500' },
};

function riskScoreColor(score: number): string {
  if (score >= 0.75) return 'text-red-600 dark:text-red-400';
  if (score >= 0.5) return 'text-orange-600 dark:text-orange-400';
  if (score >= 0.25) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-green-600 dark:text-green-400';
}

function riskBarColor(score: number): string {
  if (score >= 0.75) return 'bg-red-500';
  if (score >= 0.5) return 'bg-orange-500';
  if (score >= 0.25) return 'bg-yellow-500';
  return 'bg-green-500';
}

function actionBadgeVariant(action: string): { bg: string; text: string; icon: React.ReactNode } {
  const a = action?.toLowerCase() || '';
  if (a.includes('reject') || a.includes('block'))
    return { bg: 'bg-red-100 dark:bg-red-950/40', text: 'text-red-700 dark:text-red-300', icon: <AlertTriangle className="h-4 w-4" /> };
  if (a.includes('review') || a.includes('manual') || a.includes('escalate'))
    return { bg: 'bg-yellow-100 dark:bg-yellow-950/40', text: 'text-yellow-700 dark:text-yellow-300', icon: <ShieldAlert className="h-4 w-4" /> };
  if (a.includes('approve') || a.includes('auto'))
    return { bg: 'bg-green-100 dark:bg-green-950/40', text: 'text-green-700 dark:text-green-300', icon: <CheckCircle className="h-4 w-4" /> };
  return { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-300', icon: <Info className="h-4 w-4" /> };
}

function RiskAssessmentCard({
  riskAssessment,
  riskFlags,
  riskScore,
  riskLevel,
}: {
  riskAssessment?: RiskAssessment;
  riskFlags: RiskFlag[];
  riskScore?: number;
  riskLevel?: string;
}) {
  const [expanded, setExpanded] = useState(true);
  const score = riskAssessment?.risk_score ?? riskScore ?? 0;
  const level = (riskAssessment?.risk_level || riskLevel || 'LOW').toUpperCase() as RiskLevel;
  const flags = riskAssessment?.risk_flags ?? riskFlags;
  const pct = Math.min(Math.round(score * 100), 100);

  const componentScores = riskAssessment
    ? [
        { key: 'duplicate', score: riskAssessment.duplicate_risk_score ?? 0 },
        { key: 'vendor', score: riskAssessment.vendor_risk_score ?? 0 },
        { key: 'matching', score: riskAssessment.matching_risk_score ?? 0 },
        { key: 'price', score: riskAssessment.price_risk_score ?? 0 },
        { key: 'amount', score: riskAssessment.amount_risk_score ?? 0 },
        { key: 'pattern', score: riskAssessment.pattern_risk_score ?? 0 },
      ]
    : [];

  const borderColor =
    level === 'CRITICAL'
      ? 'border-red-500 dark:border-red-700'
      : level === 'HIGH'
        ? 'border-red-300 dark:border-red-800'
        : level === 'MEDIUM'
          ? 'border-yellow-300 dark:border-yellow-800'
          : 'border-green-300 dark:border-green-800';

  return (
    <Card className={borderColor}>
      <CardHeader
        className="cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-5 w-5 text-muted-foreground" />
            <div>
              <CardTitle className="text-base">Risk Assessment</CardTitle>
              <CardDescription>
                {flags.length} flag{flags.length !== 1 ? 's' : ''} detected
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Overall score pill */}
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${riskScoreColor(score)}`}>
                {pct}%
              </span>
              <RiskBadge level={level} />
            </div>
            {expanded ? (
              <ChevronUp className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-6">
          {/* Overall risk bar */}
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-muted-foreground">Overall Risk Score</span>
              <span className={`font-semibold ${riskScoreColor(score)}`}>
                {score.toFixed(2)} / 1.00
              </span>
            </div>
            <div className="h-3 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${riskBarColor(score)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* Recommended Action */}
          {riskAssessment?.recommended_action && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">Recommended Action</h4>
              {(() => {
                const v = actionBadgeVariant(riskAssessment.recommended_action);
                return (
                  <div className={`flex items-start gap-2 p-3 rounded-lg ${v.bg}`}>
                    <span className={`mt-0.5 ${v.text}`}>{v.icon}</span>
                    <div>
                      <span className={`font-semibold text-sm ${v.text}`}>
                        {riskAssessment.recommended_action.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      {riskAssessment.action_reason && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {riskAssessment.action_reason}
                        </p>
                      )}
                      {riskAssessment.requires_manual_review && (
                        <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1 font-medium">
                          ⚠ Manual review required
                        </p>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* Component Score Breakdown */}
          {componentScores.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">Component Score Breakdown</h4>
              <div className="space-y-3">
                {componentScores.map(({ key, score: cs }) => {
                  const meta = COMPONENT_WEIGHTS[key];
                  const csPct = Math.min(Math.round(cs * 100), 100);
                  return (
                    <div key={key}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-muted-foreground">
                          {meta.label}{' '}
                          <span className="text-muted-foreground/60">
                            ({meta.weight}% weight)
                          </span>
                        </span>
                        <span className={`font-medium ${riskScoreColor(cs)}`}>
                          {cs.toFixed(2)}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${riskBarColor(cs)}`}
                          style={{ width: `${csPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Detailed Info Sections */}
          {riskAssessment?.duplicate_info && (
            <div className="space-y-1">
              <h4 className="text-sm font-semibold">Duplicate Detection Details</h4>
              <div className="text-xs bg-muted p-3 rounded-lg space-y-1">
                {riskAssessment.duplicate_info.is_duplicate !== undefined && (
                  <p>
                    <span className="text-muted-foreground">Is Duplicate:</span>{' '}
                    <span className={riskAssessment.duplicate_info.is_duplicate ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
                      {riskAssessment.duplicate_info.is_duplicate ? 'Yes' : 'No'}
                    </span>
                  </p>
                )}
                {riskAssessment.duplicate_info.duplicate_type && (
                  <p>
                    <span className="text-muted-foreground">Type:</span>{' '}
                    {riskAssessment.duplicate_info.duplicate_type}
                  </p>
                )}
                {riskAssessment.duplicate_info.similarity_score !== undefined && (
                  <p>
                    <span className="text-muted-foreground">Similarity:</span>{' '}
                    {(riskAssessment.duplicate_info.similarity_score * 100).toFixed(1)}%
                  </p>
                )}
                {riskAssessment.duplicate_info.original_invoice_id && (
                  <p>
                    <span className="text-muted-foreground">Original Invoice:</span>{' '}
                    {riskAssessment.duplicate_info.original_invoice_id}
                  </p>
                )}
              </div>
            </div>
          )}

          {riskAssessment?.vendor_risk_info && (
            <div className="space-y-1">
              <h4 className="text-sm font-semibold">Vendor Risk Details</h4>
              <div className="text-xs bg-muted p-3 rounded-lg space-y-1">
                {riskAssessment.vendor_risk_info.vendor_status && (
                  <p>
                    <span className="text-muted-foreground">Vendor Status:</span>{' '}
                    {riskAssessment.vendor_risk_info.vendor_status}
                  </p>
                )}
                {riskAssessment.vendor_risk_info.risk_profile_score !== undefined && (
                  <p>
                    <span className="text-muted-foreground">Profile Risk Score:</span>{' '}
                    {riskAssessment.vendor_risk_info.risk_profile_score}
                  </p>
                )}
                {riskAssessment.vendor_risk_info.vendor_found !== undefined && (
                  <p>
                    <span className="text-muted-foreground">Vendor Found:</span>{' '}
                    {riskAssessment.vendor_risk_info.vendor_found ? 'Yes' : 'No'}
                  </p>
                )}
              </div>
            </div>
          )}

          {riskAssessment?.price_anomaly_info && (
            <div className="space-y-1">
              <h4 className="text-sm font-semibold">Price Anomaly Details</h4>
              <div className="text-xs bg-muted p-3 rounded-lg space-y-1">
                {riskAssessment.price_anomaly_info.has_anomaly !== undefined && (
                  <p>
                    <span className="text-muted-foreground">Has Anomaly:</span>{' '}
                    <span className={riskAssessment.price_anomaly_info.has_anomaly ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
                      {riskAssessment.price_anomaly_info.has_anomaly ? 'Yes' : 'No'}
                    </span>
                  </p>
                )}
                {riskAssessment.price_anomaly_info.anomaly_details &&
                  Array.isArray(riskAssessment.price_anomaly_info.anomaly_details) &&
                  riskAssessment.price_anomaly_info.anomaly_details.map((d: Record<string, unknown>, i: number) => (
                    <p key={i}>
                      <span className="text-muted-foreground">{String(d.description || `Anomaly ${i + 1}`)}:</span>{' '}
                      deviation {typeof d.deviation_percent === 'number' ? d.deviation_percent.toFixed(1) : '?'}%
                    </p>
                  ))}
              </div>
            </div>
          )}

          {/* Risk Flags */}
          {flags.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">
                Risk Flags ({flags.length})
              </h4>
              <div className="space-y-2">
                {flags.map((flag: RiskFlag, index: number) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-950/20"
                  >
                    <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <RiskBadge level={(flag.severity?.toUpperCase?.() || 'MEDIUM') as RiskLevel} />
                        <span className="font-medium text-sm">{flag.flag_type?.replace(/_/g, ' ')}</span>
                        {flag.confidence !== undefined && (
                          <span className="text-xs text-muted-foreground ml-auto">
                            Confidence: {(flag.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{flag.description}</p>
                      {(flag.expected_value || flag.actual_value) && (
                        <div className="flex gap-4 mt-1 text-xs">
                          {flag.expected_value && (
                            <span className="text-muted-foreground">
                              Expected: <span className="text-foreground font-medium">{flag.expected_value}</span>
                            </span>
                          )}
                          {flag.actual_value && (
                            <span className="text-muted-foreground">
                              Actual: <span className="text-foreground font-medium">{flag.actual_value}</span>
                            </span>
                          )}
                          {flag.deviation && (
                            <span className="text-red-600 dark:text-red-400 font-medium">
                              Deviation: {flag.deviation}
                            </span>
                          )}
                        </div>
                      )}
                      {flag.evidence && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Evidence: {flag.evidence}
                        </p>
                      )}
                      {flag.suggested_action && (
                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                          Suggested: {flag.suggested_action}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assessment metadata */}
          {riskAssessment?.assessed_at && (
            <div className="text-xs text-muted-foreground pt-2 border-t flex items-center gap-4">
              <span>
                Assessed: {format(new Date(riskAssessment.assessed_at), 'MMM d, yyyy HH:mm')}
              </span>
              {riskAssessment.assessed_by && (
                <span>By: {riskAssessment.assessed_by}</span>
              )}
              {riskAssessment.assessment_version && (
                <span>Version: {riskAssessment.assessment_version}</span>
              )}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

export default function InvoiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const invoiceId = params?.id as string;
  const [showPDFViewer, setShowPDFViewer] = useState(true);
  const [showProcessingLogs, setShowProcessingLogs] = useState(false);

  const { data: invoice, isLoading, error } = useInvoice(invoiceId);
  const { data: matchingResult } = useInvoiceMatchingResult(invoiceId);
  const { data: processingEvents, isLoading: processingLoading } = useInvoiceProcessingEvents(invoiceId, 1, 50);
  const { data: workflow } = useApprovalWorkflow(invoiceId);
  const { data: history } = useApprovalHistory(invoiceId);
  const retryOCRMutation = useRetryOCR();

  const handleRetryOCR = async () => {
    try {
      await retryOCRMutation.mutateAsync(invoiceId);
      toast.success('OCR processing restarted');
    } catch (error) {
      toast.error('Failed to retry OCR');
    }
  };

  const handleFieldClick = (fieldName: string, currentValue: any) => {
    const newValue = prompt(`Edit ${fieldName}:`, currentValue);
    if (newValue && newValue !== currentValue) {
      // TODO: Implement field update API
      toast.success(`${fieldName} will be updated to: ${newValue}`);
    }
  };

  const shouldShowApprovalReview =
    invoice?.status === 'RISK_REVIEW' ||
    invoice?.status === 'PENDING_APPROVAL';

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
            {shouldShowApprovalReview && (
              <Button className="gap-2" onClick={() => router.push(`/approvals/${invoiceId}`)}>
                <FileText className="h-4 w-4" />
                Review for Approval
              </Button>
            )}
          </div>
        </div>

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

        {/* Risk Assessment */}
        {(invoice.risk_assessment || (invoice.risk_flags && invoice.risk_flags.length > 0)) && (
          <RiskAssessmentCard
            riskAssessment={invoice.risk_assessment}
            riskFlags={invoice.risk_flags || []}
            riskScore={invoice.risk_score}
            riskLevel={invoice.risk_level}
          />
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
                        ${parseFloat(String(item.unit_price || 0)).toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right">
                        ${parseFloat(String(item.line_total || 0)).toFixed(2)}
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

        {/* PO Matching Result */}
        {matchingResult && <MatchingResultCard result={matchingResult} />}

        {/* Processing Logs - Collapsible */}
        <Card>
          <CardHeader 
            className="cursor-pointer hover:bg-muted/50 transition-colors" 
            onClick={() => setShowProcessingLogs(!showProcessingLogs)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-muted-foreground" />
                <div>
                  <CardTitle className="text-base">Processing Logs</CardTitle>
                  <CardDescription>
                    Step-by-step logs for upload, extraction, matching, risk, and decision.
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/processing?entity_type=invoice&entity_id=${encodeURIComponent(invoiceId)}`);
                  }}
                >
                  Open in Logs
                </Button>
                {showProcessingLogs ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            </div>
          </CardHeader>
          {showProcessingLogs && (
            <CardContent>
              <ProcessingEventsTable
                events={processingEvents?.items}
                isLoading={processingLoading}
                emptyMessage="No processing logs yet for this invoice."
              />
            </CardContent>
          )}
        </Card>

      </div>
    </DashboardLayout>
  );
}
