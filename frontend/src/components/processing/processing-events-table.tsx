'use client';

import { useMemo, useState } from 'react';
import type { ProcessingEvent } from '@/types';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { format } from 'date-fns';

function statusVariant(status: ProcessingEvent['status']) {
  switch (status) {
    case 'succeeded':
      return 'success';
    case 'failed':
      return 'destructive';
    case 'started':
    default:
      return 'secondary';
  }
}

function levelVariant(level: ProcessingEvent['level']) {
  switch (level) {
    case 'ERROR':
      return 'destructive';
    case 'WARNING':
      return 'warning';
    case 'DEBUG':
      return 'outline';
    case 'INFO':
    default:
      return 'secondary';
  }
}

export function ProcessingEventsTable({
  events,
  isLoading,
  emptyMessage = 'No events found',
}: {
  events: ProcessingEvent[] | undefined;
  isLoading?: boolean;
  emptyMessage?: string;
}) {
  const [openEventId, setOpenEventId] = useState<number | null>(null);

  const sorted = useMemo(() => {
    return (events ?? []).slice().sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
  }, [events]);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading events…</p>;
  }

  if (!sorted.length) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[170px]">Time</TableHead>
            <TableHead className="w-[140px]">Entity</TableHead>
            <TableHead className="w-[140px]">Stage</TableHead>
            <TableHead className="w-[110px]">Status</TableHead>
            <TableHead className="w-[110px]">Level</TableHead>
            <TableHead>Message</TableHead>
            <TableHead className="w-[90px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((evt) => {
            const created = evt.created_at ? new Date(evt.created_at) : null;
            const isOpen = openEventId === evt.id;
            return (
              <TableRow key={evt.id} className={evt.status === 'failed' ? 'bg-destructive/5' : undefined}>
                <TableCell className="text-xs text-muted-foreground">
                  {created ? format(created, 'yyyy-MM-dd HH:mm:ss') : '—'}
                </TableCell>
                <TableCell className="text-xs">
                  <div className="font-medium">{evt.entity_type}</div>
                  <div className="text-muted-foreground truncate max-w-[120px]" title={evt.entity_id}>
                    {evt.entity_id}
                  </div>
                </TableCell>
                <TableCell className="text-xs">{evt.stage}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(evt.status)} size="sm">
                    {evt.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={levelVariant(evt.level)} size="sm">
                    {evt.level}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm">{evt.message}</TableCell>
                <TableCell>
                  <Dialog open={isOpen} onOpenChange={(open) => setOpenEventId(open ? evt.id : null)}>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm">
                        Details
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>Processing Event</DialogTitle>
                        <DialogDescription>
                          {evt.entity_type}:{evt.entity_id} • {evt.stage}
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-3">
                        <div className="flex flex-wrap gap-2">
                          <Badge variant={statusVariant(evt.status)}>{evt.status}</Badge>
                          <Badge variant={levelVariant(evt.level)}>{evt.level}</Badge>
                          {evt.correlation_id ? <Badge variant="outline">req:{evt.correlation_id}</Badge> : null}
                        </div>
                        <div className="text-sm">
                          <div className="font-medium">Message</div>
                          <div className="text-muted-foreground">{evt.message}</div>
                        </div>
                        <div className="text-sm">
                          <div className="font-medium">Details</div>
                          <pre className="mt-1 max-h-[50vh] overflow-auto rounded-md bg-muted p-3 text-xs">
{JSON.stringify(evt.details ?? {}, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
