/**
 * Signer Progress Component
 * Displays signing progress with visual indicators
 */

import { CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  formatSignerName,
  formatSignerRole,
  formatSignerStatus,
  getSignerStatusColor,
  calculateSigningProgress,
} from '@/lib/api/esign';
import type { Signer } from '@/lib/api/esign-types';

interface SignerProgressProps {
  signers: Signer[];
  showProgress?: boolean;
  className?: string;
}

export function SignerProgress({
  signers,
  showProgress = true,
  className,
}: SignerProgressProps) {
  const progress = calculateSigningProgress(signers);
  const sortedSigners = [...signers].sort((a, b) => a.order - b.order);

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'signed':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'declined':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'expired':
        return <AlertCircle className="h-5 w-5 text-orange-600" />;
      case 'pending':
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <div className={className}>
      {showProgress && (
        <div className="mb-4">
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium">Signing Progress</span>
            <span className="text-sm text-muted-foreground">{progress}%</span>
          </div>
          <Progress value={progress} />
        </div>
      )}

      <div className="space-y-3">
        {sortedSigners.map((signer, index) => (
          <div
            key={signer.id || index}
            className="flex items-start gap-3 p-3 rounded-lg border bg-card"
          >
            <div className="mt-0.5">{getStatusIcon(signer.status)}</div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium truncate">
                  {formatSignerName(signer)}
                </span>
                <Badge variant={getSignerStatusColor(signer.status || 'pending')} size="sm">
                  {formatSignerStatus(signer.status || 'pending')}
                </Badge>
              </div>
              
              <div className="text-sm text-muted-foreground mt-1">
                {formatSignerRole(signer.role)} • Order #{signer.order + 1}
              </div>
              
              <div className="text-sm text-muted-foreground truncate mt-0.5">
                {signer.email}
              </div>

              {signer.signed_at && (
                <div className="text-xs text-muted-foreground mt-1">
                  Signed: {new Date(signer.signed_at).toLocaleString()}
                </div>
              )}

              {signer.declined_at && (
                <div className="text-xs text-red-600 mt-1">
                  Declined: {signer.decline_reason || 'No reason provided'}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
