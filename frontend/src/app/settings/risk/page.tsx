'use client';

import { useMemo, useState } from 'react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

import type { RiskSettings } from '@/types';
import { useRiskSettings, useResetRiskSettings, useUpdateRiskSettings } from '@/lib/api/settings';

function numberOr(value: string | number, fallback: number) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function getErrorDetail(err: unknown, fallback: string) {
  if (isRecord(err) && 'response' in err) {
    const response = (err as Record<string, unknown>).response;
    if (isRecord(response) && 'data' in response) {
      const data = (response as Record<string, unknown>).data;
      if (isRecord(data) && typeof data.detail === 'string') return data.detail;
    }
  }
  return fallback;
}

export default function RiskSettingsPage() {
  const { data, isLoading, error } = useRiskSettings();
  const updateMutation = useUpdateRiskSettings();
  const resetMutation = useResetRiskSettings();

  const [draft, setDraft] = useState<Partial<RiskSettings>>({});

  const form = useMemo(() => {
    if (!data) return null;
    return { ...data, ...draft } as RiskSettings;
  }, [data, draft]);

  const weightSum = useMemo(() => {
    if (!form) return 0;
    return (
      numberOr(form.weight_duplicate, 0) +
      numberOr(form.weight_vendor, 0) +
      numberOr(form.weight_price, 0) +
      numberOr(form.weight_amount, 0) +
      numberOr(form.weight_matching, 0) +
      numberOr(form.weight_pattern, 0)
    );
  }, [form]);

  const onSave = async () => {
    if (!form) return;
    try {
      const { id: _id, name: _name, ...payload } = form;
      void _id;
      void _name;
      await updateMutation.mutateAsync(payload);
      setDraft({});
      toast.success('Risk settings saved');
    } catch (e: unknown) {
      toast.error(getErrorDetail(e, 'Failed to save settings'));
    }
  };

  const onReset = async () => {
    try {
      await resetMutation.mutateAsync();
      setDraft({});
      toast.success('Restored default risk settings');
    } catch (e: unknown) {
      toast.error(getErrorDetail(e, 'Failed to restore defaults'));
    }
  };

  if (isLoading || !form) {
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
        <div className="p-6">
          <Card>
            <CardHeader>
              <CardTitle>Risk Settings</CardTitle>
              <CardDescription>Unable to load settings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground">
                {error instanceof Error ? error.message : String(error)}
              </div>
            </CardContent>
          </Card>
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
            <h2 className="text-3xl font-bold tracking-tight">Risk Settings</h2>
            <p className="text-muted-foreground">
              Configure risk detection thresholds and component weights.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onReset} disabled={resetMutation.isPending}>
              Restore Defaults
            </Button>
            <Button onClick={onSave} disabled={updateMutation.isPending}>
              Save Changes
            </Button>
          </div>
        </div>

        {/* Component Weights */}
        <Card>
          <CardHeader>
            <CardTitle>Component Weights</CardTitle>
            <CardDescription>
              Controls how much each risk dimension contributes to the overall score (current sum:{' '}
              <span className={Math.abs(weightSum - 1) < 0.01 ? 'text-green-600 font-medium' : 'text-destructive font-medium'}>
                {weightSum.toFixed(2)}
              </span>
              ). Should sum to 1.00.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="weight_duplicate">Duplicate Detection</Label>
              <Input
                id="weight_duplicate"
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={form.weight_duplicate}
                onChange={(e) => setDraft((prev) => ({ ...prev, weight_duplicate: numberOr(e.target.value, 0) }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weight_vendor">Vendor Risk</Label>
              <Input
                id="weight_vendor"
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={form.weight_vendor}
                onChange={(e) => setDraft((prev) => ({ ...prev, weight_vendor: numberOr(e.target.value, 0) }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weight_price">Price Anomaly</Label>
              <Input
                id="weight_price"
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={form.weight_price}
                onChange={(e) => setDraft((prev) => ({ ...prev, weight_price: numberOr(e.target.value, 0) }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weight_amount">Amount Risk</Label>
              <Input
                id="weight_amount"
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={form.weight_amount}
                onChange={(e) => setDraft((prev) => ({ ...prev, weight_amount: numberOr(e.target.value, 0) }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weight_matching">PO Matching Risk</Label>
              <Input
                id="weight_matching"
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={form.weight_matching}
                onChange={(e) => setDraft((prev) => ({ ...prev, weight_matching: numberOr(e.target.value, 0) }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weight_pattern">Pattern Risk</Label>
              <Input
                id="weight_pattern"
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={form.weight_pattern}
                onChange={(e) => setDraft((prev) => ({ ...prev, weight_pattern: numberOr(e.target.value, 0) }))}
              />
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Price Anomaly Detection */}
          <Card>
            <CardHeader>
              <CardTitle>Price Anomaly Detection</CardTitle>
              <CardDescription>
                Flags invoices with unusual amounts compared to vendor history.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="price_std_dev_threshold">Std-Dev Threshold</Label>
                <Input
                  id="price_std_dev_threshold"
                  type="number"
                  step="0.1"
                  min={0}
                  value={form.price_std_dev_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, price_std_dev_threshold: numberOr(e.target.value, 0) }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Number of standard deviations above the historical mean to flag.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="price_min_historical_invoices">Min Historical Invoices</Label>
                <Input
                  id="price_min_historical_invoices"
                  type="number"
                  step="1"
                  min={1}
                  value={form.price_min_historical_invoices}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      price_min_historical_invoices: numberOr(e.target.value, 1),
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="price_significant_amount">Significant Amount ($)</Label>
                <Input
                  id="price_significant_amount"
                  type="number"
                  step="100"
                  min={0}
                  value={form.price_significant_amount}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, price_significant_amount: numberOr(e.target.value, 0) }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Only flag invoices above this dollar amount.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="price_minor_increase">Minor (%)</Label>
                  <Input
                    id="price_minor_increase"
                    type="number"
                    step="0.01"
                    min={0}
                    max={1}
                    value={form.price_minor_increase}
                    onChange={(e) =>
                      setDraft((prev) => ({ ...prev, price_minor_increase: numberOr(e.target.value, 0) }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="price_major_increase">Major (%)</Label>
                  <Input
                    id="price_major_increase"
                    type="number"
                    step="0.01"
                    min={0}
                    max={1}
                    value={form.price_major_increase}
                    onChange={(e) =>
                      setDraft((prev) => ({ ...prev, price_major_increase: numberOr(e.target.value, 0) }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="price_critical_increase">Critical (%)</Label>
                  <Input
                    id="price_critical_increase"
                    type="number"
                    step="0.01"
                    min={0}
                    max={1}
                    value={form.price_critical_increase}
                    onChange={(e) =>
                      setDraft((prev) => ({ ...prev, price_critical_increase: numberOr(e.target.value, 0) }))
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Duplicate Detection */}
          <Card>
            <CardHeader>
              <CardTitle>Duplicate Detection</CardTitle>
              <CardDescription>
                Controls look-back windows and amount tolerance for finding duplicates.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="duplicate_exact_days">Exact Duplicate Look-back (days)</Label>
                <Input
                  id="duplicate_exact_days"
                  type="number"
                  step="1"
                  min={1}
                  value={form.duplicate_exact_days}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, duplicate_exact_days: numberOr(e.target.value, 1) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duplicate_fuzzy_days">Fuzzy Duplicate Look-back (days)</Label>
                <Input
                  id="duplicate_fuzzy_days"
                  type="number"
                  step="1"
                  min={1}
                  value={form.duplicate_fuzzy_days}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, duplicate_fuzzy_days: numberOr(e.target.value, 1) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duplicate_amount_tolerance">Amount Tolerance (0-1)</Label>
                <Input
                  id="duplicate_amount_tolerance"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.duplicate_amount_tolerance}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, duplicate_amount_tolerance: numberOr(e.target.value, 0) }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  e.g. 0.02 = ±2% tolerance when comparing amounts.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Vendor Risk */}
        <Card>
          <CardHeader>
            <CardTitle>Vendor Risk</CardTitle>
            <CardDescription>
              Thresholds for classifying vendor risk levels and activity windows.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="vendor_low_risk_threshold">Low Risk (&le;)</Label>
                <Input
                  id="vendor_low_risk_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.vendor_low_risk_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, vendor_low_risk_threshold: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vendor_medium_risk_threshold">Medium Risk (&le;)</Label>
                <Input
                  id="vendor_medium_risk_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.vendor_medium_risk_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      vendor_medium_risk_threshold: numberOr(e.target.value, 0),
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vendor_high_risk_threshold">High Risk (&le;)</Label>
                <Input
                  id="vendor_high_risk_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.vendor_high_risk_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      vendor_high_risk_threshold: numberOr(e.target.value, 0),
                    }))
                  }
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="vendor_good_payment_reliability">Good Payment Reliability (0-1)</Label>
                <Input
                  id="vendor_good_payment_reliability"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.vendor_good_payment_reliability}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      vendor_good_payment_reliability: numberOr(e.target.value, 0),
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vendor_acceptable_payment_reliability">
                  Acceptable Payment Reliability (0-1)
                </Label>
                <Input
                  id="vendor_acceptable_payment_reliability"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.vendor_acceptable_payment_reliability}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      vendor_acceptable_payment_reliability: numberOr(e.target.value, 0),
                    }))
                  }
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="vendor_inactive_days">Inactive Vendor (days)</Label>
                <Input
                  id="vendor_inactive_days"
                  type="number"
                  step="1"
                  min={1}
                  value={form.vendor_inactive_days}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, vendor_inactive_days: numberOr(e.target.value, 1) }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Vendors with no activity in this many days are flagged as inactive.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="vendor_new_vendor_days">New Vendor Window (days)</Label>
                <Input
                  id="vendor_new_vendor_days"
                  type="number"
                  step="1"
                  min={1}
                  value={form.vendor_new_vendor_days}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, vendor_new_vendor_days: numberOr(e.target.value, 1) }))
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Vendors onboarded within this window are considered &quot;new.&quot;
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
