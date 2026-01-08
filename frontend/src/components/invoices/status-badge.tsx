import { InvoiceStatus, RiskLevel } from '@/types';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: InvoiceStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const statusConfig: Record<InvoiceStatus, { label: string; className: string }> = {
    INGESTED: {
      label: 'Ingested',
      className: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    },
    EXTRACTED: {
      label: 'Extracted',
      className: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    },
    MATCHED: {
      label: 'Matched',
      className: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300',
    },
    RISK_REVIEW: {
      label: 'Risk Review',
      className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    },
    APPROVED: {
      label: 'Approved',
      className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    },
    REJECTED: {
      label: 'Rejected',
      className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    },
    READY_FOR_PAYMENT: {
      label: 'Ready for Payment',
      className: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
    },
    ARCHIVED: {
      label: 'Archived',
      className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    },
  };

  const config = statusConfig[status];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}

interface RiskBadgeProps {
  level: RiskLevel;
  className?: string;
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  const riskConfig: Record<RiskLevel, { label: string; className: string }> = {
    LOW: {
      label: 'Low Risk',
      className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    },
    MEDIUM: {
      label: 'Medium Risk',
      className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    },
    HIGH: {
      label: 'High Risk',
      className: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
    },
    CRITICAL: {
      label: 'Critical Risk',
      className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    },
  };

  const config = riskConfig[level];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
