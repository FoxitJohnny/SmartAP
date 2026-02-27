'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useMemo, useState } from 'react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ProcessingEventsTable } from '@/components/processing/processing-events-table';
import { useProcessingEvents, useClearProcessingEvents } from '@/lib/api/processing';
import type { ProcessingEventFilters, } from '@/lib/api/processing';
import { toast } from 'sonner';
import type { ProcessingEventLevel, ProcessingEventStatus } from '@/types';

export default function ProcessingPage() {
  return (
    <Suspense>
      <ProcessingPageContent />
    </Suspense>
  );
}

function ProcessingPageContent() {
  const searchParams = useSearchParams();

  const [entityType, setEntityType] = useState<string>(() => searchParams.get('entity_type') ?? 'invoice');
  const [entityId, setEntityId] = useState<string>(() => searchParams.get('entity_id') ?? '');
  const [stage, setStage] = useState<string>(() => searchParams.get('stage') ?? '');
  const [status, setStatus] = useState<ProcessingEventStatus | ''>(
    () => (searchParams.get('status') as ProcessingEventStatus) ?? ''
  );
  const [level, setLevel] = useState<ProcessingEventLevel | ''>(
    () => (searchParams.get('level') as ProcessingEventLevel) ?? ''
  );
  const [q, setQ] = useState<string>(() => searchParams.get('q') ?? '');

  const filters: ProcessingEventFilters = useMemo(() => {
    return {
      entity_type: entityType || undefined,
      entity_id: entityId || undefined,
      stage: stage || undefined,
      status: (status || undefined) as ProcessingEventStatus | undefined,
      level: (level || undefined) as ProcessingEventLevel | undefined,
      q: q || undefined,
    };
  }, [entityType, entityId, stage, status, level, q]);

  const { data, isLoading, refetch, isFetching } = useProcessingEvents(1, 100, filters);
  const clearMutation = useClearProcessingEvents();
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const handleClearLogs = async () => {
    try {
      const result = await clearMutation.mutateAsync();
      toast.success(`Cleared ${result.deleted} processing log(s)`);
      setShowClearConfirm(false);
    } catch {
      toast.error('Failed to clear logs');
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Processing Logs</h2>
            <p className="text-muted-foreground">See what succeeded, what failed, and why.</p>
          </div>
          <div>
            {showClearConfirm ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Clear all logs?</span>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleClearLogs}
                  disabled={clearMutation.isPending}
                >
                  {clearMutation.isPending ? 'Clearing…' : 'Confirm'}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowClearConfirm(false)}
                  disabled={clearMutation.isPending}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowClearConfirm(true)}
                disabled={!data?.total}
              >
                Clear Logs
              </Button>
            )}
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
            <CardDescription>Filter by entity and stage to quickly find issues.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>Entity Type</Label>
                <Select value={entityType} onValueChange={setEntityType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select entity type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="invoice">invoice</SelectItem>
                    <SelectItem value="po">po</SelectItem>
                    <SelectItem value="approval">approval</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Entity ID</Label>
                <Input value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="e.g. document_id" />
              </div>

              <div className="space-y-2">
                <Label>Stage</Label>
                <Input value={stage} onChange={(e) => setStage(e.target.value)} placeholder="upload / extract / match / risk / decision" />
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={status || 'all'} onValueChange={(v) => setStatus(v === 'all' ? '' : (v as ProcessingEventStatus))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">all</SelectItem>
                    <SelectItem value="started">started</SelectItem>
                    <SelectItem value="succeeded">succeeded</SelectItem>
                    <SelectItem value="failed">failed</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Level</Label>
                <Select value={level || 'all'} onValueChange={(v) => setLevel(v === 'all' ? '' : (v as ProcessingEventLevel))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">all</SelectItem>
                    <SelectItem value="DEBUG">DEBUG</SelectItem>
                    <SelectItem value="INFO">INFO</SelectItem>
                    <SelectItem value="WARNING">WARNING</SelectItem>
                    <SelectItem value="ERROR">ERROR</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Search</Label>
                <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search message…" />
              </div>
            </div>

            <div className="mt-4 flex gap-2">
              <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
                {isFetching ? 'Refreshing…' : 'Refresh'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setEntityType('invoice');
                  setEntityId('');
                  setStage('');
                  setStatus('');
                  setLevel('');
                  setQ('');
                }}
              >
                Clear
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Events</CardTitle>
            <CardDescription>
              Showing {data?.items?.length ?? 0} of {data?.total ?? 0}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ProcessingEventsTable events={data?.items} isLoading={isLoading} />
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
