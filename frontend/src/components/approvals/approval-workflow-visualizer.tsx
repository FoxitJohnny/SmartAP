'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { CheckCircle, Clock, XCircle, AlertCircle, ArrowRight } from 'lucide-react';
import type { ApprovalWorkflow } from '@/lib/api/approvals';
import { format } from 'date-fns';

interface ApprovalWorkflowVisualizerProps {
  workflow: ApprovalWorkflow;
  className?: string;
}

export function ApprovalWorkflowVisualizer({
  workflow,
  className = '',
}: ApprovalWorkflowVisualizerProps) {
  const getStepIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'PENDING':
        return <Clock className="h-6 w-6 text-yellow-500" />;
      case 'SKIPPED':
        return <XCircle className="h-6 w-6 text-gray-400" />;
      case 'NOT_REQUIRED':
        return <AlertCircle className="h-6 w-6 text-gray-300" />;
      default:
        return <Clock className="h-6 w-6 text-gray-400" />;
    }
  };

  const getStepColor = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'border-green-500 bg-green-50 dark:bg-green-950';
      case 'PENDING':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950';
      case 'SKIPPED':
        return 'border-gray-300 bg-gray-50 dark:bg-gray-900';
      case 'NOT_REQUIRED':
        return 'border-gray-200 bg-gray-50 dark:bg-gray-900';
      default:
        return 'border-gray-300 bg-muted';
    }
  };

  return (
    <Card className={`p-6 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Approval Workflow</h3>

      {/* Workflow Steps */}
      <div className="space-y-4">
        {workflow.steps.map((step, index) => (
          <div key={index}>
            <div
              className={`flex items-start gap-4 p-4 rounded-lg border-2 transition-all ${getStepColor(
                step.status
              )}`}
            >
              {/* Icon */}
              <div className="flex-shrink-0 mt-1">{getStepIcon(step.status)}</div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="font-semibold text-sm">
                    {step.role.replace(/_/g, ' ')}
                    {index === workflow.current_step && (
                      <span className="ml-2 text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded">
                        Current Step
                      </span>
                    )}
                  </h4>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded ${
                      step.status === 'COMPLETED'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : step.status === 'PENDING'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                    }`}
                  >
                    {step.status}
                  </span>
                </div>

                {step.user_name && (
                  <p className="text-sm text-muted-foreground">
                    {step.status === 'COMPLETED' ? 'Completed by' : 'Assigned to'}:{' '}
                    <span className="font-medium">{step.user_name}</span>
                  </p>
                )}

                {step.timestamp && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {format(new Date(step.timestamp), 'MMM d, yyyy h:mm a')}
                  </p>
                )}

                {step.comment && (
                  <p className="text-sm mt-2 p-2 bg-background rounded border italic">
                    "{step.comment}"
                  </p>
                )}
              </div>
            </div>

            {/* Arrow between steps */}
            {index < workflow.steps.length - 1 && (
              <div className="flex justify-center my-2">
                <ArrowRight className="h-5 w-5 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Escalation Rules */}
      {workflow.escalation_rules && (
        <div className="mt-6 p-4 bg-muted rounded-lg">
          <h4 className="font-semibold text-sm mb-2">Escalation Rules</h4>
          <ul className="text-sm text-muted-foreground space-y-1">
            {workflow.escalation_rules.amount_threshold && (
              <li>
                • Amounts over ${workflow.escalation_rules.amount_threshold.toLocaleString()}{' '}
                require additional approval
              </li>
            )}
            {workflow.escalation_rules.requires_manager && (
              <li>• Manager approval required</li>
            )}
            {workflow.escalation_rules.requires_auditor && (
              <li>• Auditor review required for high-risk invoices</li>
            )}
          </ul>
        </div>
      )}
    </Card>
  );
}
