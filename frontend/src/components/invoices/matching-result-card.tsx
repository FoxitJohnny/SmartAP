'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import type { MatchingResult, MatchingDiscrepancy } from '@/types';

function severityVariant(severity: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (severity) {
    case 'critical':
      return 'destructive';
    case 'high':
      return 'default';
    case 'medium':
      return 'secondary';
    default:
      return 'outline';
  }
}

function formatPct(v?: number | null) {
  if (v === undefined || v === null || Number.isNaN(v)) return '—';
  return `${Math.round(v * 100)}%`;
}

export function MatchingResultCard({ result }: { result: MatchingResult }) {
  const ai = result.ai_evaluation;
  const aiDecision = typeof ai === 'object' && ai ? (ai.decision ?? ai.Decision) : null;
  const aiConfidence = typeof ai === 'object' && ai ? ai.confidence : null;
  const aiReasoning = typeof ai === 'object' && ai ? ai.reasoning : null;

  const discrepancies: MatchingDiscrepancy[] = result.discrepancies || [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>PO Matching</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant={result.matched ? 'default' : 'secondary'}>
            {result.matched ? 'Matched' : 'Not Matched'}
          </Badge>
          {result.requires_approval && <Badge variant="destructive">Needs Review</Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div>
            <div className="text-sm text-muted-foreground">PO Number</div>
            <div className="font-medium">{result.po_number || '—'}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Match Type</div>
            <div className="font-medium">{result.match_type}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Overall Score</div>
            <div className="flex items-center gap-3">
              <div className="min-w-16 font-medium">{formatPct(result.match_score)}</div>
              <Progress value={Math.round((result.match_score || 0) * 100)} className="h-2" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">Vendor</div>
            <div className="font-medium">{formatPct(result.vendor_match_score)}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">Amount</div>
            <div className="font-medium">{formatPct(result.amount_match_score)}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">Line Items</div>
            <div className="font-medium">{formatPct(result.line_items_match_score)}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">Date</div>
            <div className="font-medium">{formatPct(result.date_match_score)}</div>
          </div>
        </div>

        {result.approval_reason && (
          <div className="rounded-md border p-3">
            <div className="text-sm text-muted-foreground">Approval Reason</div>
            <div className="text-sm">{result.approval_reason}</div>
          </div>
        )}

        {(aiDecision || aiReasoning || aiConfidence !== null) && (
          <div className="rounded-md border p-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">AI Evaluation</div>
              {aiDecision && <Badge variant="outline">{String(aiDecision)}</Badge>}
            </div>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
              <div>
                <div className="text-xs text-muted-foreground">Confidence</div>
                <div className="text-sm">{aiConfidence === null || aiConfidence === undefined ? '—' : formatPct(Number(aiConfidence))}</div>
              </div>
              <div className="sm:col-span-2">
                <div className="text-xs text-muted-foreground">Reasoning</div>
                <div className="text-sm">{aiReasoning || '—'}</div>
              </div>
            </div>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">Discrepancies</div>
            <div className="text-sm text-muted-foreground">{discrepancies.length}</div>
          </div>
          {discrepancies.length === 0 ? (
            <div className="mt-2 text-sm text-muted-foreground">No discrepancies detected.</div>
          ) : (
            <div className="mt-2 space-y-2">
              {discrepancies.map((d, idx) => (
                <div key={idx} className="flex items-start justify-between gap-3 rounded-md border p-3">
                  <div>
                    <div className="text-sm font-medium">{d.description}</div>
                    <div className="text-xs text-muted-foreground">
                      {d.discrepancy_type}
                      {d.line_number ? ` · line ${d.line_number}` : ''}
                    </div>
                  </div>
                  <Badge variant={severityVariant(d.severity)}>{d.severity}</Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
