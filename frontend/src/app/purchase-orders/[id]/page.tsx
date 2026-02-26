'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  usePurchaseOrder,
  usePOMatchedInvoices,
  usePOMatchingHistory,
  useClosePurchaseOrder,
  useCancelPurchaseOrder,
  type POMatchedInvoice,
} from '@/lib/api/purchase-orders';
import {
  ArrowLeftIcon,
  RefreshCwIcon,
  EditIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  AlertCircleIcon,
  FileTextIcon,
  PackageIcon,
  TrendingUpIcon,
  ArrowRightLeftIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  EyeIcon,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { DualPdfViewer } from '@/components/invoices/dual-pdf-viewer';

export default function PurchaseOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const poId = params.id as string;

  const { data: po, isLoading, error } = usePurchaseOrder(poId);
  const { data: matchedInvoices } = usePOMatchedInvoices(poId);
  const { data: matchingHistory } = usePOMatchingHistory(poId);

  const closePOMutation = useClosePurchaseOrder();
  const cancelPOMutation = useCancelPurchaseOrder();

  const [isEditing, setIsEditing] = useState(false);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [pdfViewerInvoiceId, setPdfViewerInvoiceId] = useState<string | null>(null);

  const handleClose = async () => {
    if (!confirm('Are you sure you want to close this purchase order?')) return;
    
    try {
      await closePOMutation.mutateAsync(poId);
      toast.success('Purchase order closed successfully');
    } catch (error) {
      toast.error('Failed to close purchase order');
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this purchase order?')) return;
    
    try {
      await cancelPOMutation.mutateAsync(poId);
      toast.success('Purchase order cancelled successfully');
    } catch (error) {
      toast.error('Failed to cancel purchase order');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OPEN':
        return <ClockIcon className="h-4 w-4" />;
      case 'PARTIALLY_MATCHED':
      case 'PARTIALLY_RECEIVED':
        return <AlertCircleIcon className="h-4 w-4" />;
      case 'CLOSED':
        return <CheckCircleIcon className="h-4 w-4" />;
      case 'CANCELLED':
        return <XCircleIcon className="h-4 w-4" />;
      default:
        return <ClockIcon className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'OPEN':
        return 'bg-blue-100 text-blue-700';
      case 'PARTIALLY_MATCHED':
      case 'PARTIALLY_RECEIVED':
        return 'bg-yellow-100 text-yellow-700';
      case 'CLOSED':
        return 'bg-green-100 text-green-700';
      case 'CANCELLED':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const formatStatus = (status: string) => {
    return status.replace(/_/g, ' ');
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-screen">
          <RefreshCwIcon className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    );
  }

  if (error || !po) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-screen gap-4">
          <AlertCircleIcon className="h-12 w-12 text-red-500" />
          <p className="text-lg text-muted-foreground">Purchase order not found</p>
          <Button onClick={() => router.push('/purchase-orders')}>
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Purchase Orders
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const matchingPercentage = po.total_amount > 0
    ? ((po.matched_amount / po.total_amount) * 100).toFixed(1)
    : '0';

  const linkedInvoicesCount = matchedInvoices?.length ?? po.matched_invoices_count;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.push('/purchase-orders')}>
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h2 className="text-3xl font-bold tracking-tight">PO {po.po_number}</h2>
              <p className="text-muted-foreground">{po.vendor_name}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {po.status === 'OPEN' || po.status === 'PARTIALLY_MATCHED' ? (
              <>
                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                  <EditIcon className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button variant="outline" size="sm" onClick={handleClose}>
                  <CheckCircleIcon className="h-4 w-4 mr-2" />
                  Close PO
                </Button>
                <Button variant="destructive" size="sm" onClick={handleCancel}>
                  <XCircleIcon className="h-4 w-4 mr-2" />
                  Cancel PO
                </Button>
              </>
            ) : null}
          </div>
        </div>

        {/* Overview Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
              <PackageIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <Badge className={`${getStatusColor(po.status)} flex items-center gap-1 w-fit`}>
                {getStatusIcon(po.status)}
                {formatStatus(po.status)}
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Amount</CardTitle>
              <TrendingUpIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${po.total_amount.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Matched Amount</CardTitle>
              <CheckCircleIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${po.matched_amount.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">{matchingPercentage}% matched</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Linked Invoices</CardTitle>
              <FileTextIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{linkedInvoicesCount}</div>
            </CardContent>
          </Card>
        </div>

        {/* PO Details */}
        <Card>
          <CardHeader>
            <CardTitle>Purchase Order Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">PO Number</p>
                <p className="mt-1 font-medium">{po.po_number}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Vendor</p>
                <p className="mt-1 font-medium">{po.vendor_name}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Created Date</p>
                <p className="mt-1">{format(new Date(po.created_date), 'MMM d, yyyy')}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Expected Delivery</p>
                <p className="mt-1">
                  {po.expected_delivery_date
                    ? format(new Date(po.expected_delivery_date), 'MMM d, yyyy')
                    : 'Not specified'}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Created By</p>
                <p className="mt-1">{po.created_by}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Last Updated</p>
                <p className="mt-1">{format(new Date(po.last_updated), 'MMM d, yyyy h:mm a')}</p>
              </div>
            </div>
            {po.notes && (
              <div className="mt-4">
                <p className="text-sm font-medium text-muted-foreground">Notes</p>
                <p className="mt-1 text-sm">{po.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Line Items */}
        <Card>
          <CardHeader>
            <CardTitle>Line Items</CardTitle>
            <CardDescription>{po.line_items.length} items</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium">Line #</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Description</th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Quantity</th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Unit Price</th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Total</th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Received</th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Matched</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {po.line_items.map((item) => (
                    <tr key={item.id}>
                      <td className="px-4 py-3 text-sm">{item.line_number}</td>
                      <td className="px-4 py-3 text-sm">{item.description}</td>
                      <td className="px-4 py-3 text-sm text-right">{item.quantity}</td>
                      <td className="px-4 py-3 text-sm text-right">
                        ${item.unit_price.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-medium">
                        ${item.total_amount.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-right">{item.received_quantity}</td>
                      <td className="px-4 py-3 text-sm text-right">{item.matched_quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Matched Invoices — Side-by-Side Comparison */}
        {matchedInvoices && matchedInvoices.length > 0 && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <ArrowRightLeftIcon className="h-5 w-5" />
                    Matched Invoices
                  </CardTitle>
                  <CardDescription>{matchedInvoices.length} invoice{matchedInvoices.length !== 1 ? 's' : ''} linked — click to compare side-by-side</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {matchedInvoices.map((invoice: POMatchedInvoice) => {
                const isExpanded = selectedInvoiceId === invoice.id;
                return (
                  <div key={invoice.id} className="rounded-lg border">
                    {/* Invoice header row — clickable */}
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors text-left"
                      onClick={() => setSelectedInvoiceId(isExpanded ? null : invoice.id)}
                    >
                      <div className="flex items-center gap-4">
                        <FileTextIcon className="h-5 w-5 text-muted-foreground shrink-0" />
                        <div>
                          <span className="font-medium">{invoice.invoice_number}</span>
                          <span className="text-muted-foreground text-sm ml-3">
                            {format(new Date(invoice.invoice_date), 'MMM d, yyyy')}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm font-medium">${invoice.total_amount.toLocaleString()}</span>
                        {invoice.match_score != null && (
                          <Badge variant="outline" className="text-xs">
                            {(invoice.match_score * 100).toFixed(0)}% match
                          </Badge>
                        )}
                        <Badge variant="outline">{invoice.status}</Badge>
                        {isExpanded ? (
                          <ChevronUpIcon className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDownIcon className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                    </button>

                    {/* Expanded side-by-side comparison */}
                    {isExpanded && (
                      <div className="border-t bg-muted/20 p-4">
                        {/* Header summary */}
                        <div className="grid grid-cols-2 gap-4 mb-4">
                          <div className="rounded-lg border bg-background p-3">
                            <div className="flex items-center gap-2 mb-2">
                              <PackageIcon className="h-4 w-4 text-blue-600" />
                              <span className="font-semibold text-sm text-blue-600">Purchase Order</span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div>
                                <span className="text-muted-foreground">PO #:</span>{' '}
                                <span className="font-medium">{po.po_number}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Vendor:</span>{' '}
                                <span className="font-medium">{po.vendor_name}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Total:</span>{' '}
                                <span className="font-bold">${po.total_amount.toLocaleString()}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Items:</span>{' '}
                                <span className="font-medium">{po.line_items.length}</span>
                              </div>
                            </div>
                          </div>
                          <div className="rounded-lg border bg-background p-3">
                            <div className="flex items-center gap-2 mb-2">
                              <FileTextIcon className="h-4 w-4 text-green-600" />
                              <span className="font-semibold text-sm text-green-600">Invoice</span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div>
                                <span className="text-muted-foreground">Invoice #:</span>{' '}
                                <span className="font-medium">{invoice.invoice_number}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Date:</span>{' '}
                                <span className="font-medium">{format(new Date(invoice.invoice_date), 'MMM d, yyyy')}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Total:</span>{' '}
                                <span className="font-bold">${invoice.total_amount.toLocaleString()}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Items:</span>{' '}
                                <span className="font-medium">{invoice.line_items?.length ?? 0}</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Amount comparison bar */}
                        {(() => {
                          const diff = invoice.total_amount - po.total_amount;
                          const pct = po.total_amount > 0 ? ((diff / po.total_amount) * 100) : 0;
                          const isMatch = Math.abs(diff) < 0.01;
                          return (
                            <div className={`rounded-lg border p-3 mb-4 flex items-center justify-between ${isMatch ? 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900' : 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-900'}`}>
                              <div className="flex items-center gap-2 text-sm">
                                {isMatch ? (
                                  <CheckCircleIcon className="h-4 w-4 text-green-600" />
                                ) : (
                                  <AlertCircleIcon className="h-4 w-4 text-yellow-600" />
                                )}
                                <span className="font-medium">
                                  {isMatch ? 'Totals match exactly' : `Variance: $${Math.abs(diff).toFixed(2)} (${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%)`}
                                </span>
                              </div>
                              <div className="text-sm text-muted-foreground">
                                PO ${po.total_amount.toLocaleString()} vs Invoice ${invoice.total_amount.toLocaleString()}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Side-by-side line items */}
                        <div className="grid grid-cols-2 gap-4">
                          {/* PO Line Items */}
                          <div>
                            <h4 className="text-sm font-semibold text-blue-600 mb-2 flex items-center gap-1">
                              <PackageIcon className="h-3.5 w-3.5" />
                              PO Line Items
                            </h4>
                            <div className="rounded-md border overflow-hidden">
                              <table className="w-full text-xs">
                                <thead className="bg-blue-50 dark:bg-blue-950/30">
                                  <tr>
                                    <th className="px-2 py-2 text-left font-medium">#</th>
                                    <th className="px-2 py-2 text-left font-medium">Description</th>
                                    <th className="px-2 py-2 text-right font-medium">Qty</th>
                                    <th className="px-2 py-2 text-right font-medium">Price</th>
                                    <th className="px-2 py-2 text-right font-medium">Total</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y">
                                  {po.line_items.map((item) => (
                                    <tr key={item.id}>
                                      <td className="px-2 py-1.5">{item.line_number}</td>
                                      <td className="px-2 py-1.5 max-w-[160px] truncate" title={item.description}>{item.description}</td>
                                      <td className="px-2 py-1.5 text-right">{item.quantity}</td>
                                      <td className="px-2 py-1.5 text-right">${item.unit_price.toFixed(2)}</td>
                                      <td className="px-2 py-1.5 text-right font-medium">${item.total_amount.toLocaleString()}</td>
                                    </tr>
                                  ))}
                                  <tr className="bg-muted/30 font-semibold">
                                    <td colSpan={4} className="px-2 py-1.5 text-right">Total</td>
                                    <td className="px-2 py-1.5 text-right">${po.total_amount.toLocaleString()}</td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {/* Invoice Line Items */}
                          <div>
                            <h4 className="text-sm font-semibold text-green-600 mb-2 flex items-center gap-1">
                              <FileTextIcon className="h-3.5 w-3.5" />
                              Invoice Line Items
                            </h4>
                            <div className="rounded-md border overflow-hidden">
                              <table className="w-full text-xs">
                                <thead className="bg-green-50 dark:bg-green-950/30">
                                  <tr>
                                    <th className="px-2 py-2 text-left font-medium">#</th>
                                    <th className="px-2 py-2 text-left font-medium">Description</th>
                                    <th className="px-2 py-2 text-right font-medium">Qty</th>
                                    <th className="px-2 py-2 text-right font-medium">Price</th>
                                    <th className="px-2 py-2 text-right font-medium">Total</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y">
                                  {(invoice.line_items ?? []).map((item, idx) => {
                                    // Check if this line matches the corresponding PO line
                                    const poLine = po.line_items[idx];
                                    const qtyMatch = poLine && item.quantity === poLine.quantity;
                                    const priceMatch = poLine && Math.abs(item.unit_price - poLine.unit_price) < 0.01;
                                    const totalMatch = poLine && Math.abs(item.amount - poLine.total_amount) < 0.01;
                                    return (
                                      <tr key={idx}>
                                        <td className="px-2 py-1.5">{item.line_number}</td>
                                        <td className="px-2 py-1.5 max-w-[160px] truncate" title={item.description}>{item.description}</td>
                                        <td className={`px-2 py-1.5 text-right ${qtyMatch === false ? 'text-red-600 font-medium' : ''}`}>{item.quantity}</td>
                                        <td className={`px-2 py-1.5 text-right ${priceMatch === false ? 'text-red-600 font-medium' : ''}`}>${item.unit_price.toFixed(2)}</td>
                                        <td className={`px-2 py-1.5 text-right font-medium ${totalMatch === false ? 'text-red-600' : ''}`}>${item.amount.toLocaleString()}</td>
                                      </tr>
                                    );
                                  })}
                                  <tr className="bg-muted/30 font-semibold">
                                    <td colSpan={4} className="px-2 py-1.5 text-right">Total</td>
                                    <td className="px-2 py-1.5 text-right">${invoice.total_amount.toLocaleString()}</td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </div>

                        {/* Per-line match/mismatch indicators */}
                        {(invoice.line_items ?? []).length > 0 && po.line_items.length > 0 && (
                          <div className="mt-4 rounded-lg border p-3">
                            <h4 className="text-sm font-semibold mb-2">Line-by-Line Comparison</h4>
                            <div className="space-y-1.5">
                              {po.line_items.map((poLine, idx) => {
                                const invLine = (invoice.line_items ?? [])[idx];
                                if (!invLine) {
                                  return (
                                    <div key={idx} className="flex items-center gap-2 text-xs px-2 py-1 rounded bg-red-50 dark:bg-red-950/20">
                                      <XCircleIcon className="h-3.5 w-3.5 text-red-500 shrink-0" />
                                      <span className="text-muted-foreground">Line {poLine.line_number}:</span>
                                      <span className="font-medium text-red-600">Missing on invoice</span>
                                    </div>
                                  );
                                }
                                const descMatch = poLine.description.toLowerCase() === invLine.description.toLowerCase();
                                const qtyMatch = poLine.quantity === invLine.quantity;
                                const priceMatch = Math.abs(poLine.unit_price - invLine.unit_price) < 0.01;
                                const allMatch = descMatch && qtyMatch && priceMatch;
                                const differences: string[] = [];
                                if (!descMatch) differences.push(`Description: "${poLine.description}" vs "${invLine.description}"`);
                                if (!qtyMatch) differences.push(`Qty: ${poLine.quantity} vs ${invLine.quantity}`);
                                if (!priceMatch) differences.push(`Price: $${poLine.unit_price.toFixed(2)} vs $${invLine.unit_price.toFixed(2)}`);

                                return (
                                  <div key={idx} className={`flex items-start gap-2 text-xs px-2 py-1 rounded ${allMatch ? 'bg-green-50 dark:bg-green-950/20' : 'bg-yellow-50 dark:bg-yellow-950/20'}`}>
                                    {allMatch ? (
                                      <CheckCircleIcon className="h-3.5 w-3.5 text-green-500 shrink-0 mt-0.5" />
                                    ) : (
                                      <AlertCircleIcon className="h-3.5 w-3.5 text-yellow-500 shrink-0 mt-0.5" />
                                    )}
                                    <div>
                                      <span className="text-muted-foreground">Line {poLine.line_number}:</span>{' '}
                                      <span className="font-medium">{poLine.description}</span>
                                      {allMatch ? (
                                        <span className="text-green-600 ml-1">— Exact match</span>
                                      ) : (
                                        <span className="text-yellow-600 ml-1">— {differences.join('; ')}</span>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                              {/* Extra invoice lines not on PO */}
                              {(invoice.line_items ?? []).slice(po.line_items.length).map((invLine, idx) => (
                                <div key={`extra-${idx}`} className="flex items-center gap-2 text-xs px-2 py-1 rounded bg-yellow-50 dark:bg-yellow-950/20">
                                  <AlertCircleIcon className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
                                  <span className="text-muted-foreground">Invoice Line {invLine.line_number}:</span>
                                  <span className="font-medium text-yellow-600">Extra — not on PO ({invLine.description})</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* PDF side-by-side toggle + viewer */}
                        <div className="mt-4">
                          <div className="flex items-center justify-between">
                            <Button
                              variant={pdfViewerInvoiceId === invoice.id ? 'default' : 'outline'}
                              size="sm"
                              onClick={() =>
                                setPdfViewerInvoiceId(
                                  pdfViewerInvoiceId === invoice.id ? null : invoice.id,
                                )
                              }
                            >
                              <FileTextIcon className="h-4 w-4 mr-2" />
                              {pdfViewerInvoiceId === invoice.id
                                ? 'Hide PDF Comparison'
                                : 'Compare PDFs Side-by-Side'}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => router.push(`/invoices/${invoice.id}`)}
                            >
                              <EyeIcon className="h-4 w-4 mr-2" />
                              View Full Invoice
                            </Button>
                          </div>

                          {pdfViewerInvoiceId === invoice.id && (
                            <div className="mt-3">
                              <DualPdfViewer
                                leftUrl={`/api/v1/purchase-orders/${poId}/pdf`}
                                leftLabel={`PO ${po.po_number}`}
                                leftFileName={`PO-${po.po_number}.pdf`}
                                rightUrl={`/api/v1/invoices/${invoice.id}/pdf`}
                                rightLabel={`Invoice ${invoice.invoice_number}`}
                                rightFileName={`Invoice-${invoice.invoice_number}.pdf`}
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}

        {/* Matching History */}
        {matchingHistory && matchingHistory.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Matching History</CardTitle>
              <CardDescription>Invoice matching audit trail</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {matchingHistory.map((history) => (
                  <div key={history.id} className="flex items-start gap-3 pb-4 border-b last:border-0">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700">
                      <CheckCircleIcon className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        Invoice {history.invoice_number || history.invoice_id} matched
                      </p>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>${(history.matched_amount || 0).toLocaleString()} matched</span>
                        <span>•</span>
                        <span>{history.line_items_matched || 0} line items</span>
                        <span>•</span>
                        <span>{history.matched_by || 'System'}</span>
                        <span>•</span>
                        <span>{history.matched_date ? format(new Date(history.matched_date), 'MMM d, yyyy h:mm a') : 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
