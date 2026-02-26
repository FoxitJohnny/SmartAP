'use client';

import { useMemo, useState } from 'react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';

import type { MatchingSettings } from '@/types';
import { useMatchingSettings, useResetMatchingSettings, useUpdateMatchingSettings } from '@/lib/api/settings';

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

export default function MatchingSettingsPage() {
  const { data, isLoading, error } = useMatchingSettings();
  const updateMutation = useUpdateMatchingSettings();
  const resetMutation = useResetMatchingSettings();

  const [draft, setDraft] = useState<Partial<MatchingSettings>>({});

  const form = useMemo(() => {
    if (!data) return null;
    return { ...data, ...draft } as MatchingSettings;
  }, [data, draft]);

  const weightSum = useMemo(() => {
    if (!form) return 0;
    return (
      numberOr(form.vendor_match_weight, 0) +
      numberOr(form.amount_match_weight, 0) +
      numberOr(form.line_items_match_weight, 0) +
      numberOr(form.date_match_weight, 0)
    );
  }, [form]);

  const onSave = async () => {
    if (!form) return;

    try {
      // Backend update payload excludes id/name
      const { id: _id, name: _name, ...payload } = form;
      void _id;
      void _name;
      await updateMutation.mutateAsync(payload);
      setDraft({});
      toast.success('Matching settings saved');
    } catch (e: unknown) {
      toast.error(getErrorDetail(e, 'Failed to save settings'));
    }
  };

  const onReset = async () => {
    try {
      await resetMutation.mutateAsync();
      setDraft({});
      toast.success('Restored default matching settings');
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
              <CardTitle>Matching Settings</CardTitle>
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
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Matching Settings</h2>
            <p className="text-muted-foreground">Tune invoice-to-PO matching and restore defaults anytime.</p>
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

        <Card>
          <CardHeader>
            <CardTitle>Scoring Weights</CardTitle>
            <CardDescription>
              Weights are normalized automatically (current sum: {weightSum.toFixed(2)}).
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="vendor_match_weight">Vendor Weight</Label>
              <Input
                id="vendor_match_weight"
                type="number"
                step="0.01"
                value={form.vendor_match_weight}
                onChange={(e) => setDraft((prev) => ({ ...prev, vendor_match_weight: numberOr(e.target.value, 0) }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="amount_match_weight">Amount Weight</Label>
              <Input
                id="amount_match_weight"
                type="number"
                step="0.01"
                value={form.amount_match_weight}
                onChange={(e) => setDraft((prev) => ({ ...prev, amount_match_weight: numberOr(e.target.value, 0) }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="line_items_match_weight">Line Items Weight</Label>
              <Input
                id="line_items_match_weight"
                type="number"
                step="0.01"
                value={form.line_items_match_weight}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, line_items_match_weight: numberOr(e.target.value, 0) }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="date_match_weight">Date Weight</Label>
              <Input
                id="date_match_weight"
                type="number"
                step="0.01"
                value={form.date_match_weight}
                onChange={(e) => setDraft((prev) => ({ ...prev, date_match_weight: numberOr(e.target.value, 0) }))}
              />
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Candidate Selection</CardTitle>
              <CardDescription>Controls which POs are considered for matching.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="vendor_fuzzy_threshold">Vendor Fuzzy Threshold (0-1)</Label>
                <Input
                  id="vendor_fuzzy_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.vendor_fuzzy_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, vendor_fuzzy_threshold: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="amount_tolerance_percent">Candidate Amount Tolerance (±, 0-1)</Label>
                <Input
                  id="amount_tolerance_percent"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.amount_tolerance_percent}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, amount_tolerance_percent: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Score Tolerances</CardTitle>
              <CardDescription>Controls how score components are computed.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="amount_match_tolerance">Amount Match Tolerance (±, 0-1)</Label>
                <Input
                  id="amount_match_tolerance"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.amount_match_tolerance}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, amount_match_tolerance: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="date_tolerance_days">Date Tolerance (days)</Label>
                <Input
                  id="date_tolerance_days"
                  type="number"
                  step="1"
                  min={0}
                  value={form.date_tolerance_days}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, date_tolerance_days: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="line_item_description_threshold">Line Item Match Threshold (0-1)</Label>
                  <Input
                    id="line_item_description_threshold"
                    type="number"
                    step="0.01"
                    min={0}
                    max={1}
                    value={form.line_item_description_threshold}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        line_item_description_threshold: numberOr(e.target.value, 0),
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="line_item_amount_tolerance">Line Item Amount Tolerance (±, 0-1)</Label>
                  <Input
                    id="line_item_amount_tolerance"
                    type="number"
                    step="0.01"
                    min={0}
                    max={1}
                    value={form.line_item_amount_tolerance}
                    onChange={(e) =>
                      setDraft((prev) => ({ ...prev, line_item_amount_tolerance: numberOr(e.target.value, 0) }))
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Thresholds</CardTitle>
              <CardDescription>Controls match type classification and review decisions.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="exact_match_threshold">Exact Threshold</Label>
                <Input
                  id="exact_match_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.exact_match_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, exact_match_threshold: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="good_match_threshold">Good Threshold</Label>
                <Input
                  id="good_match_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.good_match_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, good_match_threshold: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="acceptable_match_threshold">Acceptable Threshold</Label>
                <Input
                  id="acceptable_match_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.acceptable_match_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, acceptable_match_threshold: numberOr(e.target.value, 0) }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="review_threshold">Review Threshold</Label>
                <Input
                  id="review_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.review_threshold}
                  onChange={(e) => setDraft((prev) => ({ ...prev, review_threshold: numberOr(e.target.value, 0) }))}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI & Discrepancy Policy</CardTitle>
              <CardDescription>Controls AI involvement and strictness on discrepancies.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-4 rounded-md border p-3">
                <div>
                  <div className="text-sm font-medium">Use AI for ambiguous matches</div>
                  <div className="text-xs text-muted-foreground">AI can approve or flag fuzzy/partial cases.</div>
                </div>
                <Switch
                  checked={form.use_ai_for_ambiguous}
                  onCheckedChange={(v) => setDraft((prev) => ({ ...prev, use_ai_for_ambiguous: v }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ai_confidence_threshold">AI Confidence Threshold (0-1)</Label>
                <Input
                  id="ai_confidence_threshold"
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={form.ai_confidence_threshold}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, ai_confidence_threshold: numberOr(e.target.value, 0) }))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_amount_discrepancy_for_auto_approve">Max Amount Discrepancy for Auto-Approve</Label>
                <Input
                  id="max_amount_discrepancy_for_auto_approve"
                  type="number"
                  step="0.01"
                  min={0}
                  value={form.max_amount_discrepancy_for_auto_approve}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      max_amount_discrepancy_for_auto_approve: numberOr(e.target.value, 0),
                    }))
                  }
                />
              </div>

              <div className="flex items-center justify-between gap-4 rounded-md border p-3">
                <div>
                  <div className="text-sm font-medium">Block approval on critical discrepancies</div>
                  <div className="text-xs text-muted-foreground">If enabled, any critical discrepancy forces review.</div>
                </div>
                <Switch
                  checked={form.critical_discrepancy_blocks_approval}
                  onCheckedChange={(v) => setDraft((prev) => ({ ...prev, critical_discrepancy_blocks_approval: v }))}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
