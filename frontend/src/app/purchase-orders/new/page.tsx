'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useVendors } from '@/lib/api/vendors';
import { useCreatePurchaseOrder } from '@/lib/api/purchase-orders';
import { toast } from 'sonner';
import { ArrowLeftIcon, PlusIcon, RefreshCwIcon } from 'lucide-react';

function todayISODate(): string {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export default function CreatePurchaseOrderPage() {
  const router = useRouter();

  const [poNumber, setPoNumber] = useState('');
  const [vendorId, setVendorId] = useState('');
  const [totalAmount, setTotalAmount] = useState<string>('');
  const [currency, setCurrency] = useState('USD');
  const [status, setStatus] = useState<'open' | 'partial' | 'partially_received' | 'closed' | 'cancelled'>('open');
  const [orderDate, setOrderDate] = useState(todayISODate());
  const [expectedDate, setExpectedDate] = useState('');

  const { data: vendorsResult, isLoading: vendorsLoading } = useVendors(1, {});
  const vendors = vendorsResult?.data ?? [];

  const createMutation = useCreatePurchaseOrder();

  const canSubmit = useMemo(() => {
    const amount = Number(totalAmount);
    return !!poNumber.trim() && !!vendorId && Number.isFinite(amount) && amount > 0;
  }, [poNumber, vendorId, totalAmount]);

  const handleSubmit = async () => {
    if (!canSubmit) return;

    try {
      const created = await createMutation.mutateAsync({
        po_number: poNumber.trim(),
        vendor_id: vendorId,
        total_amount: Number(totalAmount),
        currency,
        status,
        order_date: orderDate || undefined,
        expected_date: expectedDate || undefined,
      });

      toast.success('Purchase order created');
      router.push(`/purchase-orders/${encodeURIComponent(created.po_number)}`);
    } catch {
      toast.error('Failed to create purchase order');
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.push('/purchase-orders')}>
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h2 className="text-3xl font-bold tracking-tight">Create Purchase Order</h2>
              <p className="text-muted-foreground">Add a new PO for invoice matching</p>
            </div>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>PO Details</CardTitle>
            <CardDescription>Required fields: PO Number, Vendor, Total Amount</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="poNumber">PO Number</Label>
                <Input
                  id="poNumber"
                  placeholder="PO-2026-001"
                  value={poNumber}
                  onChange={(e) => setPoNumber(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label>Vendor</Label>
                <Select value={vendorId} onValueChange={setVendorId}>
                  <SelectTrigger>
                    <SelectValue placeholder={vendorsLoading ? 'Loading vendors...' : 'Select vendor'} />
                  </SelectTrigger>
                  <SelectContent>
                    {vendors.map((v) => (
                      <SelectItem key={v.id} value={v.id}>
                        {v.name} ({v.id})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="totalAmount">Total Amount</Label>
                <Input
                  id="totalAmount"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  value={totalAmount}
                  onChange={(e) => setTotalAmount(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="currency">Currency</Label>
                <Input
                  id="currency"
                  placeholder="USD"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                />
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={status} onValueChange={(v) => setStatus(v as typeof status)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="partially_received">Partially Received</SelectItem>
                    <SelectItem value="closed">Closed</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="orderDate">Order Date</Label>
                <Input
                  id="orderDate"
                  type="date"
                  value={orderDate}
                  onChange={(e) => setOrderDate(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="expectedDate">Expected Delivery</Label>
                <Input
                  id="expectedDate"
                  type="date"
                  value={expectedDate}
                  onChange={(e) => setExpectedDate(e.target.value)}
                />
              </div>
            </div>

            <div className="mt-6 flex gap-2">
              <Button variant="outline" onClick={() => router.push('/purchase-orders')}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={!canSubmit || createMutation.isPending}>
                {createMutation.isPending ? (
                  <>
                    <RefreshCwIcon className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <PlusIcon className="h-4 w-4 mr-2" />
                    Create PO
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
