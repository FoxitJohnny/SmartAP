'use client';

/**
 * Approval Dashboard Component
 * 
 * Displays approval workflows, pending approvals, and approval chain visualization.
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { CheckCircle, XCircle, Clock, AlertTriangle, RefreshCw, FileText, ChevronRight } from 'lucide-react';
import { format } from 'date-fns';

interface ApprovalLevel {
  level_number: number;
  level_name: string;
  approver_emails: string[];
  required_approvals: number;
  timeout_hours: number;
}

interface ApprovalChain {
  id: string;
  name: string;
  min_amount: number;
  max_amount: number | null;
  required_approvers: number;
  sequential_approval: boolean;
  require_esign: boolean;
  esign_threshold: number | null;
  levels: ApprovalLevel[];
}

interface ApprovalAction {
  id: string;
  level_number: number;
  approver_email: string;
  action: 'APPROVE' | 'REJECT' | 'REQUEST_INFO' | 'FORWARD' | 'ESCALATE';
  comment: string | null;
  created_at: string;
}

interface ApprovalWorkflow {
  id: string;
  invoice_id: string;
  chain_id: string;
  chain_name: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'APPROVED' | 'REJECTED' | 'ESCALATED' | 'EXPIRED' | 'CANCELLED';
  current_level: number;
  esign_required: boolean;
  esign_request_id: string | null;
  created_at: string;
  completed_at: string | null;
  expires_at: string | null;
  is_expired: boolean;
  time_remaining_hours: number | null;
  actions: ApprovalAction[];
  chain: ApprovalChain;
}

interface PendingApproval {
  workflow_id: string;
  invoice_id: string;
  invoice_number: string;
  vendor_name: string;
  amount: number;
  currency: string;
  level_name: string;
  created_at: string;
  expires_at: string | null;
  time_remaining_hours: number | null;
}

interface ApprovalDashboardProps {
  currentUserEmail?: string;
}

const getStatusBadge = (status: ApprovalWorkflow['status']) => {
  const styles: Record<string, string> = {
    PENDING: 'bg-yellow-100 text-yellow-800',
    IN_PROGRESS: 'bg-blue-100 text-blue-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
    ESCALATED: 'bg-orange-100 text-orange-800',
    EXPIRED: 'bg-gray-100 text-gray-800',
    CANCELLED: 'bg-gray-100 text-gray-800',
  };
  return <Badge className={styles[status] || 'bg-gray-100'}>{status}</Badge>;
};

export default function ApprovalDashboard({ currentUserEmail }: ApprovalDashboardProps) {
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [workflows, setWorkflows] = useState<ApprovalWorkflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<ApprovalWorkflow | null>(null);
  const [actionDialogOpen, setActionDialogOpen] = useState(false);
  const [actionType, setActionType] = useState<'approve' | 'reject'>('approve');
  const [comment, setComment] = useState('');

  useEffect(() => {
    fetchPendingApprovals();
    fetchWorkflows();
  }, []);

  const fetchPendingApprovals = async () => {
    try {
      const response = await fetch('/api/v1/approvals/pending');
      if (response.ok) {
        const data = await response.json();
        setPendingApprovals(data);
      }
    } catch (error) {
      console.error('Error fetching pending approvals:', error);
    }
  };

  const fetchWorkflows = async () => {
    try {
      const response = await fetch('/api/v1/approvals/workflows');
      if (response.ok) {
        const data = await response.json();
        setWorkflows(data);
      }
    } catch (error) {
      console.error('Error fetching workflows:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async () => {
    if (!selectedWorkflow) return;

    try {
      const response = await fetch(`/api/v1/approvals/workflows/${selectedWorkflow.id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: actionType.toUpperCase(),
          comment: comment || null,
        }),
      });

      if (response.ok) {
        fetchPendingApprovals();
        fetchWorkflows();
        setActionDialogOpen(false);
        setComment('');
      }
    } catch (error) {
      console.error('Error performing action:', error);
    }
  };

  const openActionDialog = (workflow: ApprovalWorkflow, type: 'approve' | 'reject') => {
    setSelectedWorkflow(workflow);
    setActionType(type);
    setActionDialogOpen(true);
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pending Your Approval</CardDescription>
            <CardTitle className="text-3xl">{pendingApprovals.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-muted-foreground">
              <Clock className="h-4 w-4 mr-1" />
              Awaiting action
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>In Progress</CardDescription>
            <CardTitle className="text-3xl">
              {workflows.filter(w => w.status === 'IN_PROGRESS').length}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-blue-600">
              <ChevronRight className="h-4 w-4 mr-1" />
              Being processed
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Approved Today</CardDescription>
            <CardTitle className="text-3xl text-green-600">
              {workflows.filter(w => 
                w.status === 'APPROVED' && 
                w.completed_at && 
                new Date(w.completed_at).toDateString() === new Date().toDateString()
              ).length}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-green-600">
              <CheckCircle className="h-4 w-4 mr-1" />
              Completed
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Expiring Soon</CardDescription>
            <CardTitle className="text-3xl text-orange-600">
              {pendingApprovals.filter(p => 
                p.time_remaining_hours !== null && p.time_remaining_hours < 24
              ).length}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center text-sm text-orange-600">
              <AlertTriangle className="h-4 w-4 mr-1" />
              {"< 24 hours"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Approvals */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Pending Approvals</CardTitle>
              <CardDescription>Invoices awaiting your approval</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchPendingApprovals}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {pendingApprovals.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
              <p>No pending approvals</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice</TableHead>
                  <TableHead>Vendor</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Level</TableHead>
                  <TableHead>Time Remaining</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingApprovals.map((approval) => (
                  <TableRow key={approval.workflow_id}>
                    <TableCell>
                      <div className="flex items-center">
                        <FileText className="h-4 w-4 mr-2 text-muted-foreground" />
                        {approval.invoice_number}
                      </div>
                    </TableCell>
                    <TableCell>{approval.vendor_name}</TableCell>
                    <TableCell className="font-medium">
                      {formatCurrency(approval.amount, approval.currency)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{approval.level_name}</Badge>
                    </TableCell>
                    <TableCell>
                      {approval.time_remaining_hours !== null ? (
                        <span className={approval.time_remaining_hours < 24 ? 'text-orange-600' : ''}>
                          {Math.round(approval.time_remaining_hours)}h
                        </span>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          size="sm"
                          variant="default"
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => {
                            const workflow = workflows.find(w => w.id === approval.workflow_id);
                            if (workflow) openActionDialog(workflow, 'approve');
                          }}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => {
                            const workflow = workflows.find(w => w.id === approval.workflow_id);
                            if (workflow) openActionDialog(workflow, 'reject');
                          }}
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Reject
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Recent Workflows */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Workflows</CardTitle>
          <CardDescription>All approval workflows</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice ID</TableHead>
                <TableHead>Chain</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Current Level</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>eSign</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workflows.slice(0, 10).map((workflow) => (
                <TableRow key={workflow.id}>
                  <TableCell>{workflow.invoice_id}</TableCell>
                  <TableCell>{workflow.chain_name}</TableCell>
                  <TableCell>{getStatusBadge(workflow.status)}</TableCell>
                  <TableCell>
                    Level {workflow.current_level} / {workflow.chain?.levels?.length || '-'}
                  </TableCell>
                  <TableCell>
                    {format(new Date(workflow.created_at), 'MMM d, yyyy HH:mm')}
                  </TableCell>
                  <TableCell>
                    {workflow.esign_required ? (
                      <Badge variant="secondary">Required</Badge>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Action Dialog */}
      <Dialog open={actionDialogOpen} onOpenChange={setActionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionType === 'approve' ? 'Approve Invoice' : 'Reject Invoice'}
            </DialogTitle>
            <DialogDescription>
              {actionType === 'approve'
                ? 'Please confirm your approval for this invoice.'
                : 'Please provide a reason for rejecting this invoice.'}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="comment">Comment {actionType === 'reject' && '(required)'}</Label>
            <Input
              id="comment"
              placeholder="Enter your comment..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAction}
              disabled={actionType === 'reject' && !comment}
              className={actionType === 'approve' ? 'bg-green-600 hover:bg-green-700' : ''}
              variant={actionType === 'reject' ? 'destructive' : 'default'}
            >
              {actionType === 'approve' ? 'Approve' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export { ApprovalDashboard };
