'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { CheckCircle, XCircle, ArrowUpCircle, MessageSquare } from 'lucide-react';

interface ApprovalActionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actionType: 'APPROVE' | 'REJECT' | 'ESCALATE' | 'REQUEST_CHANGES';
  invoiceNumber?: string;
  onConfirm: (data: { comment?: string; reason?: string; assignTo?: string }) => void;
  isLoading?: boolean;
}

export function ApprovalActionDialog({
  open,
  onOpenChange,
  actionType,
  invoiceNumber,
  onConfirm,
  isLoading = false,
}: ApprovalActionDialogProps) {
  const [comment, setComment] = useState('');
  const [reason, setReason] = useState('');
  const [assignTo, setAssignTo] = useState('');

  const handleConfirm = () => {
    onConfirm({
      comment: comment.trim() || undefined,
      reason: reason.trim() || undefined,
      assignTo: assignTo.trim() || undefined,
    });
    // Reset form
    setComment('');
    setReason('');
    setAssignTo('');
  };

  const handleCancel = () => {
    onOpenChange(false);
    setComment('');
    setReason('');
    setAssignTo('');
  };

  const getDialogConfig = () => {
    switch (actionType) {
      case 'APPROVE':
        return {
          icon: <CheckCircle className="h-6 w-6 text-green-500" />,
          title: 'Approve Invoice',
          description: 'Are you sure you want to approve this invoice?',
          confirmText: 'Approve',
          confirmVariant: 'default' as const,
          showComment: true,
          showReason: false,
          showAssignTo: false,
        };
      case 'REJECT':
        return {
          icon: <XCircle className="h-6 w-6 text-red-500" />,
          title: 'Reject Invoice',
          description: 'Please provide a reason for rejecting this invoice.',
          confirmText: 'Reject',
          confirmVariant: 'destructive' as const,
          showComment: true,
          showReason: true,
          showAssignTo: false,
        };
      case 'ESCALATE':
        return {
          icon: <ArrowUpCircle className="h-6 w-6 text-blue-500" />,
          title: 'Escalate Invoice',
          description: 'Escalate this invoice for additional review.',
          confirmText: 'Escalate',
          confirmVariant: 'default' as const,
          showComment: true,
          showReason: true,
          showAssignTo: true,
        };
      case 'REQUEST_CHANGES':
        return {
          icon: <MessageSquare className="h-6 w-6 text-yellow-500" />,
          title: 'Request Changes',
          description: 'Request changes or additional information for this invoice.',
          confirmText: 'Send Request',
          confirmVariant: 'default' as const,
          showComment: true,
          showReason: false,
          showAssignTo: false,
        };
      default:
        return {
          icon: null,
          title: 'Confirm Action',
          description: '',
          confirmText: 'Confirm',
          confirmVariant: 'default' as const,
          showComment: false,
          showReason: false,
          showAssignTo: false,
        };
    }
  };

  const config = getDialogConfig();
  const isRejectOrEscalate = actionType === 'REJECT' || actionType === 'ESCALATE';
  const canConfirm = !isRejectOrEscalate || (isRejectOrEscalate && reason.trim());

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            {config.icon}
            <div>
              <DialogTitle>{config.title}</DialogTitle>
              {invoiceNumber && (
                <p className="text-sm text-muted-foreground">Invoice: {invoiceNumber}</p>
              )}
            </div>
          </div>
          <DialogDescription>{config.description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {config.showReason && (
            <div className="space-y-2">
              <Label htmlFor="reason">
                Reason <span className="text-red-500">*</span>
              </Label>
              <Input
                id="reason"
                placeholder="Enter reason..."
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={isLoading}
              />
            </div>
          )}

          {config.showComment && (
            <div className="space-y-2">
              <Label htmlFor="comment">
                Comment {!config.showReason && '(Optional)'}
              </Label>
              <textarea
                id="comment"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Add any additional comments..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                disabled={isLoading}
              />
            </div>
          )}

          {config.showAssignTo && (
            <div className="space-y-2">
              <Label htmlFor="assignTo">Assign To (Optional)</Label>
              <Input
                id="assignTo"
                placeholder="Enter user email or ID..."
                value={assignTo}
                onChange={(e) => setAssignTo(e.target.value)}
                disabled={isLoading}
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant={config.confirmVariant}
            onClick={handleConfirm}
            disabled={isLoading || !canConfirm}
          >
            {isLoading ? 'Processing...' : config.confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
