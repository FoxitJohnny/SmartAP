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
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

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
              <div className="text-2xl font-bold">{po.matched_invoices_count}</div>
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

        {/* Matched Invoices */}
        {matchedInvoices && matchedInvoices.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Matched Invoices</CardTitle>
              <CardDescription>{matchedInvoices.length} invoices linked</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium">Invoice #</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
                      <th className="px-4 py-3 text-right text-sm font-medium">Total Amount</th>
                      <th className="px-4 py-3 text-right text-sm font-medium">Matched Amount</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Matched Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {matchedInvoices.map((invoice) => (
                      <tr
                        key={invoice.id}
                        className="hover:bg-muted/50 cursor-pointer"
                        onClick={() => router.push(`/invoices/${invoice.id}`)}
                      >
                        <td className="px-4 py-3 text-sm font-medium">{invoice.invoice_number}</td>
                        <td className="px-4 py-3 text-sm">
                          {format(new Date(invoice.invoice_date), 'MMM d, yyyy')}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          ${invoice.total_amount.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          ${invoice.matched_amount.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <Badge variant="outline">{invoice.status}</Badge>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {format(new Date(invoice.matched_date), 'MMM d, yyyy')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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
                        Invoice {history.invoice_number} matched
                      </p>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>${history.matched_amount.toLocaleString()} matched</span>
                        <span>•</span>
                        <span>{history.line_items_matched} line items</span>
                        <span>•</span>
                        <span>{history.matched_by}</span>
                        <span>•</span>
                        <span>{format(new Date(history.matched_date), 'MMM d, yyyy h:mm a')}</span>
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
