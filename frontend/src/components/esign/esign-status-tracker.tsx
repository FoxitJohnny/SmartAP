/**
 * eSign Status Tracker Component
 * Real-time status tracking for eSign requests
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { Loader2, RefreshCw, FileCheck, Mail, XCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ESignStatusBadge } from './esign-status-badge';
import { SignerProgress } from './signer-progress';
import {
  getESignRequest,
  sendSignerReminder,
  cancelESignRequest,
  canSendReminder,
  canCancelRequest,
  getNextPendingSigner,
} from '@/lib/api/esign';
import type { ESignRequest } from '@/lib/api/esign-types';

interface ESignStatusTrackerProps {
  requestId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onStatusChange?: (request: ESignRequest) => void;
}

export function ESignStatusTracker({
  requestId,
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
  onStatusChange,
}: ESignStatusTrackerProps) {
  const [request, setRequest] = useState<ESignRequest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchRequest = useCallback(async () => {
    try {
      const data = await getESignRequest(requestId);
      setRequest(data);
      setError(null);
      onStatusChange?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch eSign request');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [requestId, onStatusChange]);

  useEffect(() => {
    fetchRequest();

    if (autoRefresh) {
      const interval = setInterval(fetchRequest, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchRequest, autoRefresh, refreshInterval]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchRequest();
  };

  const handleSendReminder = async (signerEmail: string) => {
    setActionInProgress(`remind-${signerEmail}`);
    try {
      await sendSignerReminder(requestId, signerEmail);
      await fetchRequest();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reminder');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this signature request?')) {
      return;
    }

    const reason = prompt('Please provide a reason for cancellation:');
    if (!reason) return;

    setActionInProgress('cancel');
    try {
      await cancelESignRequest(requestId, reason);
      await fetchRequest();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel request');
    } finally {
      setActionInProgress(null);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (!request) {
    return (
      <Card>
        <CardContent className="py-8">
          <Alert variant="destructive">
            <AlertDescription>
              {error || 'eSign request not found'}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const nextSigner = getNextPendingSigner(request.signers);
  const canCancel = canCancelRequest(request.status);
  const isCompleted = ['fully_signed', 'rejected', 'expired', 'cancelled'].includes(
    request.status
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileCheck className="h-5 w-5" />
              Electronic Signature Request
            </CardTitle>
            <CardDescription>
              Created {new Date(request.created_at).toLocaleString()}
            </CardDescription>
          </div>
          
          <div className="flex items-center gap-2">
            <ESignStatusBadge status={request.status} />
            <Button
              variant="outline"
              size="icon"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
              />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Invoice Details */}
        <div className="rounded-lg border p-4 bg-muted/50">
          <h3 className="font-semibold mb-2">Invoice Details</h3>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Invoice Number:</dt>
            <dd className="font-medium">{request.invoice_number}</dd>
            
            <dt className="text-muted-foreground">Vendor:</dt>
            <dd className="font-medium">{request.vendor_name}</dd>
            
            <dt className="text-muted-foreground">Amount:</dt>
            <dd className="font-medium">
              ${request.invoice_amount.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </dd>

            <dt className="text-muted-foreground">Expires:</dt>
            <dd className="font-medium">
              {new Date(request.expires_at).toLocaleString()}
            </dd>
          </dl>
        </div>

        {/* Next Action */}
        {nextSigner && !isCompleted && (
          <Alert>
            <Mail className="h-4 w-4" />
            <AlertDescription>
              <strong>Awaiting signature from:</strong> {nextSigner.name} ({nextSigner.email})
            </AlertDescription>
          </Alert>
        )}

        {/* Completion Status */}
        {request.completed_at && (
          <Alert>
            <FileCheck className="h-4 w-4" />
            <AlertDescription>
              <strong>Completed:</strong>{' '}
              {new Date(request.completed_at).toLocaleString()}
            </AlertDescription>
          </Alert>
        )}

        {/* Cancellation Reason */}
        {request.cancelled_at && request.cancellation_reason && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Cancelled:</strong> {request.cancellation_reason}
            </AlertDescription>
          </Alert>
        )}

        {/* Error Message */}
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Signers Progress */}
        <SignerProgress signers={request.signers} />

        {/* Actions */}
        {!isCompleted && (
          <div className="flex gap-2">
            {nextSigner && canSendReminder(nextSigner) && (
              <Button
                variant="outline"
                onClick={() => handleSendReminder(nextSigner.email)}
                disabled={actionInProgress === `remind-${nextSigner.email}`}
              >
                {actionInProgress === `remind-${nextSigner.email}` ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Mail className="mr-2 h-4 w-4" />
                    Send Reminder
                  </>
                )}
              </Button>
            )}

            {canCancel && (
              <Button
                variant="destructive"
                onClick={handleCancel}
                disabled={actionInProgress === 'cancel'}
              >
                {actionInProgress === 'cancel' ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Cancelling...
                  </>
                ) : (
                  <>
                    <XCircle className="mr-2 h-4 w-4" />
                    Cancel Request
                  </>
                )}
              </Button>
            )}
          </div>
        )}

        {/* Signed Document */}
        {request.signed_document_url && (
          <div className="pt-4 border-t">
            <Button asChild className="w-full">
              <a
                href={request.signed_document_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <FileCheck className="mr-2 h-4 w-4" />
                Download Signed Document
              </a>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
