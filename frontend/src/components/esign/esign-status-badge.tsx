/**
 * eSign Status Badge Component
 * Displays the current status of an eSign request
 */

import { Badge } from '@/components/ui/badge';
import { formatStatus, getStatusColor } from '@/lib/api/esign';
import type { ESignStatus } from '@/lib/api/esign-types';

interface ESignStatusBadgeProps {
  status: ESignStatus | string;
  className?: string;
}

export function ESignStatusBadge({ status, className }: ESignStatusBadgeProps) {
  const variant = getStatusColor(status);
  const label = formatStatus(status);

  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
}
