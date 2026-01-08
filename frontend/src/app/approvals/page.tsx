'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StatusBadge, RiskBadge } from '@/components/invoices/status-badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  useApprovalQueue,
  useBulkApprove,
  useBulkReject,
  type ApprovalQueueFilters,
} from '@/lib/api/approvals';
import { format } from 'date-fns';
import { toast } from 'sonner';
import {
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Filter,
  AlertTriangle,
} from 'lucide-react';
import type { Invoice } from '@/types';

export default function ApprovalsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<ApprovalQueueFilters>({});
  const [selectedInvoices, setSelectedInvoices] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  const limit = 20;
  const { data, isLoading, error } = useApprovalQueue(page, limit, filters);
  const bulkApproveMutation = useBulkApprove();
  const bulkRejectMutation = useBulkReject();

  const invoices = data?.data || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / limit);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedInvoices(new Set(invoices.map((inv) => inv.id)));
    } else {
      setSelectedInvoices(new Set());
    }
  };

  const handleSelectInvoice = (invoiceId: string, checked: boolean) => {
    const newSelected = new Set(selectedInvoices);
    if (checked) {
      newSelected.add(invoiceId);
    } else {
      newSelected.delete(invoiceId);
    }
    setSelectedInvoices(newSelected);
  };

  const handleBulkApprove = async () => {
    if (selectedInvoices.size === 0) {
      toast.error('Please select at least one invoice');
      return;
    }

    try {
      await bulkApproveMutation.mutateAsync({
        invoice_ids: Array.from(selectedInvoices),
      });
      toast.success(`${selectedInvoices.size} invoice(s) approved`);
      setSelectedInvoices(new Set());
    } catch (error) {
      toast.error('Failed to approve invoices');
    }
  };

  const handleBulkReject = async () => {
    if (selectedInvoices.size === 0) {
      toast.error('Please select at least one invoice');
      return;
    }

    const reason = prompt('Please provide a reason for bulk rejection:');
    if (!reason) return;

    try {
      await bulkRejectMutation.mutateAsync({
        invoice_ids: Array.from(selectedInvoices),
        reason,
      });
      toast.success(`${selectedInvoices.size} invoice(s) rejected`);
      setSelectedInvoices(new Set());
    } catch (error) {
      toast.error('Failed to reject invoices');
    }
  };

  const handleFilterChange = (key: keyof ApprovalQueueFilters, value: any) => {
    setFilters({ ...filters, [key]: value });
    setPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setFilters({});
    setPage(1);
  };

  const getPriorityLevel = (invoice: Invoice): 'HIGH' | 'MEDIUM' | 'LOW' => {
    if (invoice.risk_level === 'CRITICAL' || invoice.risk_level === 'HIGH') {
      return 'HIGH';
    }
    if ((invoice.total_amount || 0) > 10000) {
      return 'HIGH';
    }
    if (invoice.risk_level === 'MEDIUM') {
      return 'MEDIUM';
    }
    return 'LOW';
  };

  const getPriorityColor = (priority: 'HIGH' | 'MEDIUM' | 'LOW') => {
    switch (priority) {
      case 'HIGH':
        return 'text-red-600 bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800';
      case 'MEDIUM':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200 dark:bg-yellow-950 dark:border-yellow-800';
      case 'LOW':
        return 'text-green-600 bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800';
    }
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

  if (error) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
          <p className="text-lg font-medium">Failed to load approval queue</p>
          <Button className="mt-4" onClick={() => window.location.reload()}>
            Retry
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
            <h2 className="text-3xl font-bold tracking-tight">Approval Queue</h2>
            <p className="text-muted-foreground">
              {total} invoice{total !== 1 ? 's' : ''} pending approval
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setShowFilters(!showFilters)}
              className="gap-2"
            >
              <Filter className="h-4 w-4" />
              {showFilters ? 'Hide' : 'Show'} Filters
            </Button>
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <Card className="p-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select
                  value={filters.priority || ''}
                  onValueChange={(value) =>
                    handleFilterChange('priority', value || undefined)
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All priorities" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All</SelectItem>
                    <SelectItem value="HIGH">High</SelectItem>
                    <SelectItem value="MEDIUM">Medium</SelectItem>
                    <SelectItem value="LOW">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Risk Level</Label>
                <Select
                  value={filters.riskLevel || ''}
                  onValueChange={(value) =>
                    handleFilterChange('riskLevel', value || undefined)
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All risk levels" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All</SelectItem>
                    <SelectItem value="LOW">Low</SelectItem>
                    <SelectItem value="MEDIUM">Medium</SelectItem>
                    <SelectItem value="HIGH">High</SelectItem>
                    <SelectItem value="CRITICAL">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Min Amount</Label>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={filters.minAmount || ''}
                  onChange={(e) =>
                    handleFilterChange('minAmount', e.target.value ? Number(e.target.value) : undefined)
                  }
                />
              </div>

              <div className="space-y-2">
                <Label>Max Amount</Label>
                <Input
                  type="number"
                  placeholder="999999.99"
                  value={filters.maxAmount || ''}
                  onChange={(e) =>
                    handleFilterChange('maxAmount', e.target.value ? Number(e.target.value) : undefined)
                  }
                />
              </div>
            </div>

            <div className="flex justify-end mt-4">
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear Filters
              </Button>
            </div>
          </Card>
        )}

        {/* Bulk Actions */}
        {selectedInvoices.size > 0 && (
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">
                {selectedInvoices.size} invoice{selectedInvoices.size !== 1 ? 's' : ''}{' '}
                selected
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkReject}
                  disabled={bulkRejectMutation.isPending}
                  className="gap-2"
                >
                  <XCircle className="h-4 w-4" />
                  Reject Selected
                </Button>
                <Button
                  size="sm"
                  onClick={handleBulkApprove}
                  disabled={bulkApproveMutation.isPending}
                  className="gap-2"
                >
                  <CheckCircle className="h-4 w-4" />
                  Approve Selected
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Approval Queue Table */}
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="p-4 w-12">
                    <Checkbox
                      checked={
                        invoices.length > 0 &&
                        selectedInvoices.size === invoices.length
                      }
                      onCheckedChange={handleSelectAll}
                    />
                  </th>
                  <th className="p-4">Priority</th>
                  <th className="p-4">Invoice #</th>
                  <th className="p-4">Vendor</th>
                  <th className="p-4">Amount</th>
                  <th className="p-4">Date</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Risk</th>
                  <th className="p-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-muted-foreground">
                      No invoices in approval queue
                    </td>
                  </tr>
                ) : (
                  invoices.map((invoice) => {
                    const priority = getPriorityLevel(invoice);
                    return (
                      <tr
                        key={invoice.id}
                        className="border-b hover:bg-muted/50 cursor-pointer"
                        onClick={() => router.push(`/invoices/${invoice.id}`)}
                      >
                        <td className="p-4" onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={selectedInvoices.has(invoice.id)}
                            onCheckedChange={(checked) =>
                              handleSelectInvoice(invoice.id, checked as boolean)
                            }
                          />
                        </td>
                        <td className="p-4">
                          <span
                            className={`text-xs font-medium px-2 py-1 rounded border ${getPriorityColor(
                              priority
                            )}`}
                          >
                            {priority}
                          </span>
                        </td>
                        <td className="p-4 font-medium">
                          {invoice.invoice_number || 'N/A'}
                        </td>
                        <td className="p-4">{invoice.vendor_name || 'Unknown'}</td>
                        <td className="p-4 font-semibold">
                          ${invoice.total_amount?.toFixed(2) || '0.00'}
                        </td>
                        <td className="p-4 text-sm text-muted-foreground">
                          {invoice.invoice_date
                            ? format(new Date(invoice.invoice_date), 'MMM d, yyyy')
                            : 'N/A'}
                        </td>
                        <td className="p-4">
                          <StatusBadge status={invoice.status} />
                        </td>
                        <td className="p-4">
                          {invoice.risk_level ? (
                            <div className="flex items-center gap-2">
                              <RiskBadge level={invoice.risk_level} />
                              {invoice.risk_flags && invoice.risk_flags.length > 0 && (
                                <span className="text-xs text-muted-foreground">
                                  ({invoice.risk_flags.length})
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">N/A</span>
                          )}
                        </td>
                        <td className="p-4" onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => router.push(`/invoices/${invoice.id}`)}
                          >
                            Review
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * limit + 1} to {Math.min(page * limit, total)} of{' '}
                {total} results
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
