'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { InvoiceFilters, InvoiceStatus } from '@/types';

interface InvoiceFiltersProps {
  filters: InvoiceFilters;
  onFiltersChange: (filters: InvoiceFilters) => void;
  onClear: () => void;
}

const statusOptions: { value: InvoiceStatus; label: string }[] = [
  { value: 'INGESTED', label: 'Ingested' },
  { value: 'EXTRACTED', label: 'Extracted' },
  { value: 'MATCHED', label: 'Matched' },
  { value: 'RISK_REVIEW', label: 'Risk Review' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'READY_FOR_PAYMENT', label: 'Ready for Payment' },
  { value: 'ARCHIVED', label: 'Archived' },
];

export function InvoiceFilters({
  filters,
  onFiltersChange,
  onClear,
}: InvoiceFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const updateFilter = <K extends keyof InvoiceFilters>(
    key: K,
    value: InvoiceFilters[K]
  ) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const hasActiveFilters =
    filters.status ||
    filters.vendor_name ||
    filters.min_amount ||
    filters.max_amount ||
    filters.start_date ||
    filters.end_date ||
    filters.has_risk_flags !== undefined;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Filters</CardTitle>
            <CardDescription>
              Filter invoices by status, vendor, amount, and more
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={onClear}>
                Clear All
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? 'Collapse' : 'Expand'}
            </Button>
          </div>
        </div>
      </CardHeader>
      {isExpanded && (
        <CardContent className="space-y-4">
          {/* Search */}
          <div className="space-y-2">
            <Label htmlFor="search">Search</Label>
            <Input
              id="search"
              placeholder="Invoice number, vendor name..."
              value={filters.search || ''}
              onChange={(e) => updateFilter('search', e.target.value)}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Status Filter */}
            <div className="space-y-2">
              <Label>Status</Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-full justify-between">
                    {filters.status
                      ? statusOptions.find((s) => s.value === filters.status)
                          ?.label
                      : 'All Statuses'}
                    <svg
                      className="ml-2 h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56">
                  <DropdownMenuCheckboxItem
                    checked={!filters.status}
                    onCheckedChange={() => updateFilter('status', undefined)}
                  >
                    All Statuses
                  </DropdownMenuCheckboxItem>
                  {statusOptions.map((option) => (
                    <DropdownMenuCheckboxItem
                      key={option.value}
                      checked={filters.status === option.value}
                      onCheckedChange={() =>
                        updateFilter('status', option.value)
                      }
                    >
                      {option.label}
                    </DropdownMenuCheckboxItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Vendor Name */}
            <div className="space-y-2">
              <Label htmlFor="vendor">Vendor Name</Label>
              <Input
                id="vendor"
                placeholder="Enter vendor name"
                value={filters.vendor_name || ''}
                onChange={(e) => updateFilter('vendor_name', e.target.value)}
              />
            </div>

            {/* Risk Flags */}
            <div className="space-y-2">
              <Label>Risk Flags</Label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-full justify-between">
                    {filters.has_risk_flags === undefined
                      ? 'All Invoices'
                      : filters.has_risk_flags
                      ? 'With Risks'
                      : 'No Risks'}
                    <svg
                      className="ml-2 h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuCheckboxItem
                    checked={filters.has_risk_flags === undefined}
                    onCheckedChange={() =>
                      updateFilter('has_risk_flags', undefined)
                    }
                  >
                    All Invoices
                  </DropdownMenuCheckboxItem>
                  <DropdownMenuCheckboxItem
                    checked={filters.has_risk_flags === true}
                    onCheckedChange={() => updateFilter('has_risk_flags', true)}
                  >
                    With Risk Flags
                  </DropdownMenuCheckboxItem>
                  <DropdownMenuCheckboxItem
                    checked={filters.has_risk_flags === false}
                    onCheckedChange={() =>
                      updateFilter('has_risk_flags', false)
                    }
                  >
                    No Risk Flags
                  </DropdownMenuCheckboxItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Amount Range */}
            <div className="space-y-2">
              <Label htmlFor="minAmount">Min Amount</Label>
              <Input
                id="minAmount"
                type="number"
                placeholder="0.00"
                value={filters.min_amount || ''}
                onChange={(e) =>
                  updateFilter(
                    'min_amount',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxAmount">Max Amount</Label>
              <Input
                id="maxAmount"
                type="number"
                placeholder="0.00"
                value={filters.max_amount || ''}
                onChange={(e) =>
                  updateFilter(
                    'max_amount',
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
              />
            </div>

            {/* Date Range */}
            <div className="space-y-2">
              <Label htmlFor="startDate">Start Date</Label>
              <Input
                id="startDate"
                type="date"
                value={filters.start_date || ''}
                onChange={(e) => updateFilter('start_date', e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="endDate">End Date</Label>
              <Input
                id="endDate"
                type="date"
                value={filters.end_date || ''}
                onChange={(e) => updateFilter('end_date', e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
