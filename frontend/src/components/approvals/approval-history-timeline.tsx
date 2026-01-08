'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { CheckCircle, XCircle, AlertCircle, MessageSquare, ArrowUpCircle } from 'lucide-react';
import type { ApprovalHistory } from '@/lib/api/approvals';
import { format } from 'date-fns';

interface ApprovalHistoryTimelineProps {
  history: ApprovalHistory[];
  className?: string;
}

export function ApprovalHistoryTimeline({
  history,
  className = '',
}: ApprovalHistoryTimelineProps) {
  const getActionIcon = (action: string) => {
    switch (action) {
      case 'APPROVE':
      case 'APPROVED':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'REJECT':
      case 'REJECTED':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'ESCALATE':
      case 'ESCALATED':
        return <ArrowUpCircle className="h-5 w-5 text-blue-500" />;
      case 'REQUEST_CHANGES':
      case 'COMMENT':
        return <MessageSquare className="h-5 w-5 text-yellow-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'APPROVE':
      case 'APPROVED':
        return 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800';
      case 'REJECT':
      case 'REJECTED':
        return 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800';
      case 'ESCALATE':
      case 'ESCALATED':
        return 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800';
      case 'REQUEST_CHANGES':
      case 'COMMENT':
        return 'bg-yellow-50 border-yellow-200 dark:bg-yellow-950 dark:border-yellow-800';
      default:
        return 'bg-muted border-muted-foreground';
    }
  };

  const formatAction = (action: string) => {
    return action
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  if (!history || history.length === 0) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold mb-4">Approval History</h3>
        <div className="text-center py-8 text-muted-foreground">
          <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No approval history yet</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`p-6 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">
        Approval History ({history.length})
      </h3>

      <div className="space-y-4">
        {history.map((item, index) => (
          <div key={item.id} className="relative">
            {/* Timeline line */}
            {index < history.length - 1 && (
              <div className="absolute left-[18px] top-10 bottom-0 w-0.5 bg-border" />
            )}

            {/* Timeline item */}
            <div className="flex gap-4">
              {/* Icon */}
              <div className="flex-shrink-0 mt-1 relative z-10 bg-background">
                {getActionIcon(item.action)}
              </div>

              {/* Content */}
              <div
                className={`flex-1 p-4 rounded-lg border ${getActionColor(item.action)}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-sm">
                      {formatAction(item.action)}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      by {item.user_name}{' '}
                      <span className="text-xs">({item.user_role.replace(/_/g, ' ')})</span>
                    </p>
                  </div>
                  <time className="text-xs text-muted-foreground">
                    {format(new Date(item.timestamp), 'MMM d, yyyy')}
                    <br />
                    {format(new Date(item.timestamp), 'h:mm a')}
                  </time>
                </div>

                {item.comment && (
                  <div className="mt-2 p-2 bg-background rounded border text-sm">
                    <p className="italic">"{item.comment}"</p>
                  </div>
                )}

                {item.reason && (
                  <div className="mt-2 p-2 bg-background rounded border text-sm">
                    <p className="font-medium text-xs text-muted-foreground mb-1">
                      Reason:
                    </p>
                    <p>{item.reason}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
