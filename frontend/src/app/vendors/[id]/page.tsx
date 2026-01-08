'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  useVendor,
  useVendorInvoiceHistory,
  useVendorRiskEvents,
  useVendorRiskHistory,
  useVendorPerformanceMetrics,
  useDeactivateVendor,
  useActivateVendor,
} from '@/lib/api/vendors';
import {
  ArrowLeftIcon,
  RefreshCwIcon,
  EditIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  ShieldIcon,
  TrendingUpIcon,
  FileTextIcon,
  ClockIcon,
  DollarSignIcon,
  BarChartIcon,
  XCircleIcon,
  MailIcon,
  PhoneIcon,
  MapPinIcon,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function VendorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const vendorId = params.id as string;

  const { data: vendor, isLoading, error } = useVendor(vendorId);
  const { data: invoiceHistory } = useVendorInvoiceHistory(vendorId);
  const { data: riskEvents } = useVendorRiskEvents(vendorId);
  const { data: riskHistory } = useVendorRiskHistory(vendorId);
  const { data: performance } = useVendorPerformanceMetrics(vendorId);

  const deactivateMutation = useDeactivateVendor();
  const activateMutation = useActivateVendor();

  const [invoicePage, setInvoicePage] = useState(1);

  const handleToggleActive = async () => {
    if (!vendor) return;

    const action = vendor.active ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${action} this vendor?`)) return;

    try {
      if (vendor.active) {
        await deactivateMutation.mutateAsync(vendorId);
        toast.success('Vendor deactivated successfully');
      } else {
        await activateMutation.mutateAsync(vendorId);
        toast.success('Vendor activated successfully');
      }
    } catch (error) {
      toast.error(`Failed to ${action} vendor`);
    }
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'LOW':
        return 'bg-green-100 text-green-700';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-700';
      case 'HIGH':
        return 'bg-orange-100 text-orange-700';
      case 'CRITICAL':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'LOW':
        return <CheckCircleIcon className="h-4 w-4" />;
      case 'MEDIUM':
      case 'HIGH':
      case 'CRITICAL':
        return <AlertTriangleIcon className="h-4 w-4" />;
      default:
        return <ShieldIcon className="h-4 w-4" />;
    }
  };

  const getEventSeverityColor = (severity: string) => {
    switch (severity) {
      case 'LOW':
        return 'bg-blue-100 text-blue-700';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-700';
      case 'HIGH':
        return 'bg-orange-100 text-orange-700';
      case 'CRITICAL':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
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

  if (error || !vendor) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-screen gap-4">
          <AlertTriangleIcon className="h-12 w-12 text-red-500" />
          <p className="text-lg text-muted-foreground">Vendor not found</p>
          <Button onClick={() => router.push('/vendors')}>
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Vendors
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
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.push('/vendors')}>
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h2 className="text-3xl font-bold tracking-tight">{vendor.name}</h2>
              <p className="text-muted-foreground">Vendor Code: {vendor.vendor_code}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <EditIcon className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button
              variant={vendor.active ? 'destructive' : 'default'}
              size="sm"
              onClick={handleToggleActive}
            >
              {vendor.active ? (
                <>
                  <XCircleIcon className="h-4 w-4 mr-2" />
                  Deactivate
                </>
              ) : (
                <>
                  <CheckCircleIcon className="h-4 w-4 mr-2" />
                  Activate
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Overview Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Risk Level</CardTitle>
              <ShieldIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <Badge className={`${getRiskLevelColor(vendor.risk_level)} flex items-center gap-1 w-fit`}>
                {getRiskIcon(vendor.risk_level)}
                {vendor.risk_level}
              </Badge>
              <p className="text-xs text-muted-foreground mt-2">Score: {vendor.risk_score}/100</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
              <FileTextIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{vendor.total_invoices}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Avg: ${vendor.avg_invoice_amount.toLocaleString()}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Amount</CardTitle>
              <DollarSignIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${vendor.total_amount.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Payment Rate</CardTitle>
              <TrendingUpIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{vendor.on_time_payment_rate.toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground mt-1">On-time payments</p>
            </CardContent>
          </Card>
        </div>

        {/* Vendor Information */}
        <Card>
          <CardHeader>
            <CardTitle>Vendor Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Contact Information</p>
                  <div className="mt-2 space-y-2">
                    {vendor.email && (
                      <div className="flex items-center gap-2 text-sm">
                        <MailIcon className="h-4 w-4 text-muted-foreground" />
                        <span>{vendor.email}</span>
                      </div>
                    )}
                    {vendor.phone && (
                      <div className="flex items-center gap-2 text-sm">
                        <PhoneIcon className="h-4 w-4 text-muted-foreground" />
                        <span>{vendor.phone}</span>
                      </div>
                    )}
                  </div>
                </div>
                {(vendor.address || vendor.city || vendor.state) && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Address</p>
                    <div className="mt-2 flex items-start gap-2 text-sm">
                      <MapPinIcon className="h-4 w-4 text-muted-foreground mt-0.5" />
                      <div>
                        {vendor.address && <div>{vendor.address}</div>}
                        {(vendor.city || vendor.state || vendor.zip) && (
                          <div>
                            {vendor.city}
                            {vendor.city && vendor.state && ', '}
                            {vendor.state} {vendor.zip}
                          </div>
                        )}
                        {vendor.country && <div>{vendor.country}</div>}
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Tax ID</p>
                  <p className="mt-1 text-sm">{vendor.tax_id || 'Not provided'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Payment Terms</p>
                  <p className="mt-1 text-sm">{vendor.payment_terms || 'Not specified'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Status</p>
                  <Badge variant={vendor.active ? 'default' : 'secondary'} className="mt-1">
                    {vendor.active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </div>
            </div>
            {vendor.notes && (
              <div className="mt-4">
                <p className="text-sm font-medium text-muted-foreground">Notes</p>
                <p className="mt-1 text-sm">{vendor.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Risk Dashboard */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Risk History Chart */}
          {riskHistory && riskHistory.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Risk Score History</CardTitle>
                <CardDescription>Risk score trends over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={riskHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="risk_score"
                      stroke="#ef4444"
                      strokeWidth={2}
                      name="Risk Score"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Performance Metrics */}
          {performance && (
            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
                <CardDescription>Key vendor statistics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Duplicate Attempts</span>
                    <Badge variant="outline">{performance.duplicate_attempts}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Price Variance Rate</span>
                    <Badge variant="outline">{performance.price_variance_rate.toFixed(1)}%</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Rejection Rate</span>
                    <Badge variant="outline">{performance.rejection_rate.toFixed(1)}%</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Avg Processing Time</span>
                    <Badge variant="outline">{performance.avg_processing_time.toFixed(1)}s</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Avg Days to Pay</span>
                    <Badge variant="outline">{performance.avg_days_to_pay.toFixed(0)} days</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Risk Events */}
        {riskEvents && riskEvents.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Risk Events</CardTitle>
              <CardDescription>Historical risk incidents and flags</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {riskEvents.slice(0, 10).map((event) => (
                  <div key={event.id} className="flex items-start gap-3 pb-4 border-b last:border-0">
                    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${getEventSeverityColor(event.severity)}`}>
                      <AlertTriangleIcon className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium">{event.event_type.replace(/_/g, ' ')}</p>
                        <Badge className={getEventSeverityColor(event.severity)} variant="outline">
                          {event.severity}
                        </Badge>
                        {event.resolved && (
                          <Badge variant="outline" className="bg-green-100 text-green-700">
                            Resolved
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{event.description}</p>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{format(new Date(event.detected_date), 'MMM d, yyyy h:mm a')}</span>
                        {event.invoice_number && (
                          <>
                            <span>•</span>
                            <span>Invoice: {event.invoice_number}</span>
                          </>
                        )}
                        {event.resolved && event.resolved_date && (
                          <>
                            <span>•</span>
                            <span>Resolved: {format(new Date(event.resolved_date), 'MMM d, yyyy')}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Invoice History */}
        {invoiceHistory && invoiceHistory.data.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Invoice History</CardTitle>
              <CardDescription>{invoiceHistory.total} invoices total</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium">Invoice #</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Due Date</th>
                      <th className="px-4 py-3 text-right text-sm font-medium">Amount</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Risk</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Payment Date</th>
                      <th className="px-4 py-3 text-center text-sm font-medium">Days to Pay</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {invoiceHistory.data.map((invoice) => (
                      <tr
                        key={invoice.id}
                        className="hover:bg-muted/50 cursor-pointer"
                        onClick={() => router.push(`/invoices/${invoice.id}`)}
                      >
                        <td className="px-4 py-3 text-sm font-medium">{invoice.invoice_number}</td>
                        <td className="px-4 py-3 text-sm">
                          {format(new Date(invoice.invoice_date), 'MMM d, yyyy')}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {format(new Date(invoice.due_date), 'MMM d, yyyy')}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          ${invoice.total_amount.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <Badge variant="outline">{invoice.status}</Badge>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <Badge variant="outline">{invoice.risk_level}</Badge>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {invoice.payment_date
                            ? format(new Date(invoice.payment_date), 'MMM d, yyyy')
                            : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-center">
                          {invoice.days_to_pay !== undefined ? `${invoice.days_to_pay} days` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
