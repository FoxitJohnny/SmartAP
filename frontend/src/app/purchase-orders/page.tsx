'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { usePurchaseOrders, PurchaseOrderFilters } from '@/lib/api/purchase-orders';
import {
  SearchIcon,
  PlusIcon,
  FilterIcon,
  RefreshCwIcon,
  DownloadIcon,
  EyeIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  AlertCircleIcon,
} from 'lucide-react';
import { format } from 'date-fns';

export default function PurchaseOrdersPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<PurchaseOrderFilters>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, error, refetch } = usePurchaseOrders(page, filters);

  const handleSearch = () => {
    setFilters({ ...filters, search: searchTerm });
    setPage(1);
  };

  const handleViewPO = (id: string) => {
    router.push(`/purchase-orders/${id}`);
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

  if (error) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-screen gap-4">
          <AlertCircleIcon className="h-12 w-12 text-red-500" />
          <p className="text-lg text-muted-foreground">Failed to load purchase orders</p>
          <Button onClick={() => refetch()}>Retry</Button>
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
            <h2 className="text-3xl font-bold tracking-tight">Purchase Orders</h2>
            <p className="text-muted-foreground">Manage purchase orders and invoice matching</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
              <FilterIcon className="h-4 w-4 mr-2" />
              Filter
            </Button>
            <Button variant="outline" size="sm">
              <DownloadIcon className="h-4 w-4 mr-2" />
              Export
            </Button>
            <Button size="sm">
              <PlusIcon className="h-4 w-4 mr-2" />
              Create PO
            </Button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by PO number, vendor name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="pl-9"
            />
          </div>
          <Button onClick={handleSearch}>Search</Button>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <Card>
            <CardHeader>
              <CardTitle>Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-medium">Status</label>
                  <select
                    className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                    value={filters.status || ''}
                    onChange={(e) => {
                      setFilters({ ...filters, status: e.target.value });
                      setPage(1);
                    }}
                  >
                    <option value="">All Statuses</option>
                    <option value="OPEN">Open</option>
                    <option value="PARTIALLY_MATCHED">Partially Matched</option>
                    <option value="CLOSED">Closed</option>
                    <option value="CANCELLED">Cancelled</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Min Amount</label>
                  <Input
                    type="number"
                    placeholder="0"
                    value={filters.min_amount || ''}
                    onChange={(e) => {
                      setFilters({ ...filters, min_amount: Number(e.target.value) });
                      setPage(1);
                    }}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Max Amount</label>
                  <Input
                    type="number"
                    placeholder="999999"
                    value={filters.max_amount || ''}
                    onChange={(e) => {
                      setFilters({ ...filters, max_amount: Number(e.target.value) });
                      setPage(1);
                    }}
                    className="mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Purchase Orders Table */}
        <Card>
          <CardHeader>
            <CardTitle>Purchase Orders</CardTitle>
            <CardDescription>
              {data?.total || 0} purchase orders found
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data && data.data.length > 0 ? (
              <div className="space-y-4">
                <div className="rounded-md border">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium">PO Number</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Vendor</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Created Date</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Expected Delivery</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Total Amount</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Matched Amount</th>
                        <th className="px-4 py-3 text-center text-sm font-medium">Invoices</th>
                        <th className="px-4 py-3 text-center text-sm font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.data.map((po) => (
                        <tr
                          key={po.id}
                          className="hover:bg-muted/50 cursor-pointer"
                          onClick={() => handleViewPO(po.id)}
                        >
                          <td className="px-4 py-3">
                            <div className="font-medium">{po.po_number}</div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-sm">{po.vendor_name}</div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge className={`${getStatusColor(po.status)} flex items-center gap-1 w-fit`}>
                              {getStatusIcon(po.status)}
                              {formatStatus(po.status)}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {format(new Date(po.created_date), 'MMM d, yyyy')}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {po.expected_delivery_date
                              ? format(new Date(po.expected_delivery_date), 'MMM d, yyyy')
                              : '-'}
                          </td>
                          <td className="px-4 py-3 text-right text-sm font-medium">
                            ${po.total_amount.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right text-sm">
                            ${po.matched_amount.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Badge variant="outline">{po.matched_invoices_count}</Badge>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewPO(po.id);
                              }}
                            >
                              <EyeIcon className="h-4 w-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {data.total > data.per_page && (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                      Showing {(page - 1) * data.per_page + 1} to{' '}
                      {Math.min(page * data.per_page, data.total)} of {data.total} results
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(page - 1)}
                        disabled={page === 1}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(page + 1)}
                        disabled={page * data.per_page >= data.total}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12">
                <AlertCircleIcon className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No purchase orders found</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Create your first purchase order to get started
                </p>
                <Button>
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Create Purchase Order
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
