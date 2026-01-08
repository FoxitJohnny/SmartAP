'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useVendors, VendorFilters } from '@/lib/api/vendors';
import {
  SearchIcon,
  PlusIcon,
  FilterIcon,
  RefreshCwIcon,
  DownloadIcon,
  EyeIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  ShieldIcon,
} from 'lucide-react';
import { format } from 'date-fns';

export default function VendorsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<VendorFilters>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, error, refetch } = useVendors(page, filters);

  const handleSearch = () => {
    setFilters({ ...filters, search: searchTerm });
    setPage(1);
  };

  const handleViewVendor = (id: string) => {
    router.push(`/vendors/${id}`);
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
          <AlertTriangleIcon className="h-12 w-12 text-red-500" />
          <p className="text-lg text-muted-foreground">Failed to load vendors</p>
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
            <h2 className="text-3xl font-bold tracking-tight">Vendors</h2>
            <p className="text-muted-foreground">Manage vendor information and risk profiles</p>
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
              Add Vendor
            </Button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by vendor name, code, email..."
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
                  <label className="text-sm font-medium">Risk Level</label>
                  <select
                    className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                    value={filters.risk_level || ''}
                    onChange={(e) => {
                      setFilters({ ...filters, risk_level: e.target.value });
                      setPage(1);
                    }}
                  >
                    <option value="">All Risk Levels</option>
                    <option value="LOW">Low Risk</option>
                    <option value="MEDIUM">Medium Risk</option>
                    <option value="HIGH">High Risk</option>
                    <option value="CRITICAL">Critical Risk</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Status</label>
                  <select
                    className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                    value={filters.active === undefined ? '' : filters.active ? 'true' : 'false'}
                    onChange={(e) => {
                      const value = e.target.value;
                      setFilters({
                        ...filters,
                        active: value === '' ? undefined : value === 'true',
                      });
                      setPage(1);
                    }}
                  >
                    <option value="">All Vendors</option>
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Min Risk Score</label>
                  <Input
                    type="number"
                    placeholder="0"
                    min="0"
                    max="100"
                    value={filters.min_risk_score || ''}
                    onChange={(e) => {
                      setFilters({ ...filters, min_risk_score: Number(e.target.value) });
                      setPage(1);
                    }}
                    className="mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Vendors Table */}
        <Card>
          <CardHeader>
            <CardTitle>Vendors</CardTitle>
            <CardDescription>
              {data?.total || 0} vendors found
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data && data.data.length > 0 ? (
              <div className="space-y-4">
                <div className="rounded-md border">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium">Vendor</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Code</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Contact</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Risk Level</th>
                        <th className="px-4 py-3 text-center text-sm font-medium">Risk Score</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Total Invoices</th>
                        <th className="px-4 py-3 text-right text-sm font-medium">Total Amount</th>
                        <th className="px-4 py-3 text-center text-sm font-medium">Payment Rate</th>
                        <th className="px-4 py-3 text-left text-sm font-medium">Last Invoice</th>
                        <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
                        <th className="px-4 py-3 text-center text-sm font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.data.map((vendor) => (
                        <tr
                          key={vendor.id}
                          className="hover:bg-muted/50 cursor-pointer"
                          onClick={() => handleViewVendor(vendor.id)}
                        >
                          <td className="px-4 py-3">
                            <div className="font-medium">{vendor.name}</div>
                          </td>
                          <td className="px-4 py-3 text-sm">{vendor.vendor_code}</td>
                          <td className="px-4 py-3">
                            <div className="text-sm">{vendor.email || '-'}</div>
                            <div className="text-xs text-muted-foreground">{vendor.phone || '-'}</div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge className={`${getRiskLevelColor(vendor.risk_level)} flex items-center gap-1 w-fit`}>
                              {getRiskIcon(vendor.risk_level)}
                              {vendor.risk_level}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="font-medium">{vendor.risk_score}</div>
                          </td>
                          <td className="px-4 py-3 text-right">{vendor.total_invoices}</td>
                          <td className="px-4 py-3 text-right font-medium">
                            ${vendor.total_amount.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Badge variant="outline">
                              {vendor.on_time_payment_rate.toFixed(1)}%
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {vendor.last_invoice_date
                              ? format(new Date(vendor.last_invoice_date), 'MMM d, yyyy')
                              : '-'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Badge variant={vendor.active ? 'default' : 'secondary'}>
                              {vendor.active ? 'Active' : 'Inactive'}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewVendor(vendor.id);
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
                <AlertTriangleIcon className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No vendors found</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Add your first vendor to get started
                </p>
                <Button>
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Add Vendor
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
