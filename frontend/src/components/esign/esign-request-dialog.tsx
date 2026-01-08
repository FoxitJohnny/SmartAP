/**
 * eSign Request Dialog Component
 * Modal for creating eSign requests
 */

'use client';

import { useState } from 'react';
import { Loader2, FileSignature, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { createESignRequest } from '@/lib/api/esign';
import { SignerProgress } from './signer-progress';
import type { CreateESignRequestParams, ESignRequest, Signer } from '@/lib/api/esign-types';

interface ESignRequestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoiceId: string;
  invoiceNumber: string;
  invoiceAmount: number;
  vendorName: string;
  requiredSigners: Signer[];
  onSuccess?: (request: ESignRequest) => void;
}

export function ESignRequestDialog({
  open,
  onOpenChange,
  invoiceId,
  invoiceNumber,
  invoiceAmount,
  vendorName,
  requiredSigners,
  onSuccess,
}: ESignRequestDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const params: CreateESignRequestParams = {
        invoice_id: invoiceId,
        signers: requiredSigners.map((signer, index) => ({
          name: signer.name,
          email: signer.email,
          role: signer.role,
        })),
      };

      const request = await createESignRequest(params);
      onSuccess?.(request);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create eSign request');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSignature className="h-5 w-5" />
            Request Electronic Signature
          </DialogTitle>
          <DialogDescription>
            This invoice requires electronic signature approval before processing.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Invoice Details */}
          <div className="rounded-lg border p-4 bg-muted/50">
            <h3 className="font-semibold mb-2">Invoice Details</h3>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-muted-foreground">Invoice Number:</dt>
              <dd className="font-medium">{invoiceNumber}</dd>
              
              <dt className="text-muted-foreground">Vendor:</dt>
              <dd className="font-medium">{vendorName}</dd>
              
              <dt className="text-muted-foreground">Amount:</dt>
              <dd className="font-medium">
                ${invoiceAmount.toLocaleString('en-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </dd>
            </dl>
          </div>

          {/* Required Signers */}
          <div>
            <h3 className="font-semibold mb-3">Required Approvers</h3>
            <SignerProgress signers={requiredSigners} showProgress={false} />
          </div>

          {/* Important Notice */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Each approver will receive an email with a secure signing link.
              The document must be signed in sequential order.
            </AlertDescription>
          </Alert>

          {/* Error Message */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              'Send for Signature'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
