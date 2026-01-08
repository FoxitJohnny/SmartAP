'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import type { Invoice } from '@/types';

interface InvoiceFieldOverlayProps {
  invoice: Invoice;
  onFieldClick?: (fieldName: string, currentValue: any) => void;
}

interface FieldInfo {
  label: string;
  value: any;
  confidence?: number;
  editable?: boolean;
}

export function InvoiceFieldOverlay({
  invoice,
  onFieldClick,
}: InvoiceFieldOverlayProps) {
  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'muted';
    if (confidence >= 0.9) return 'success';
    if (confidence >= 0.7) return 'warning';
    return 'destructive';
  };

  const getConfidenceIcon = (confidence?: number) => {
    if (!confidence) return null;
    if (confidence >= 0.9) return <CheckCircle className="h-3 w-3" />;
    if (confidence >= 0.7) return <AlertTriangle className="h-3 w-3" />;
    return <AlertCircle className="h-3 w-3" />;
  };

  const fields: FieldInfo[] = [
    {
      label: 'Invoice Number',
      value: invoice.invoice_number,
      confidence: invoice.ocr_data?.confidence?.invoice_number,
      editable: true,
    },
    {
      label: 'Vendor',
      value: invoice.vendor_name,
      confidence: invoice.ocr_data?.confidence?.vendor_name,
      editable: true,
    },
    {
      label: 'Invoice Date',
      value: invoice.invoice_date
        ? new Date(invoice.invoice_date).toLocaleDateString()
        : 'N/A',
      confidence: invoice.ocr_data?.confidence?.invoice_date,
      editable: true,
    },
    {
      label: 'Due Date',
      value: invoice.due_date
        ? new Date(invoice.due_date).toLocaleDateString()
        : 'N/A',
      confidence: invoice.ocr_data?.confidence?.due_date,
      editable: true,
    },
    {
      label: 'Total Amount',
      value: `$${invoice.total_amount?.toFixed(2) || '0.00'}`,
      confidence: invoice.ocr_data?.confidence?.total_amount,
      editable: true,
    },
    {
      label: 'Subtotal',
      value: invoice.subtotal ? `$${invoice.subtotal.toFixed(2)}` : 'N/A',
      confidence: invoice.ocr_data?.confidence?.subtotal,
      editable: true,
    },
    {
      label: 'Tax Amount',
      value: invoice.tax_amount ? `$${invoice.tax_amount.toFixed(2)}` : 'N/A',
      confidence: invoice.ocr_data?.confidence?.tax_amount,
      editable: true,
    },
    {
      label: 'PO Number',
      value: invoice.po_number || 'N/A',
      confidence: invoice.ocr_data?.confidence?.po_number,
      editable: true,
    },
    {
      label: 'Currency',
      value: invoice.currency || 'USD',
      confidence: invoice.ocr_data?.confidence?.currency,
      editable: true,
    },
  ];

  return (
    <Card className="p-4">
      <h3 className="font-semibold mb-4">Extracted Fields</h3>
      <div className="space-y-3">
        {fields.map((field) => (
          <div
            key={field.label}
            className={`p-3 border rounded-lg transition-all ${
              field.editable && onFieldClick
                ? 'cursor-pointer hover:bg-muted/50 hover:border-primary'
                : ''
            }`}
            onClick={() => {
              if (field.editable && onFieldClick) {
                onFieldClick(field.label, field.value);
              }
            }}
          >
            <div className="flex items-start justify-between mb-1">
              <span className="text-sm font-medium text-muted-foreground">
                {field.label}
              </span>
              {field.confidence !== undefined && (
                <Badge
                  variant={
                    getConfidenceColor(field.confidence) as
                      | 'default'
                      | 'secondary'
                      | 'destructive'
                      | 'outline'
                  }
                  className="text-xs"
                >
                  <span className="flex items-center gap-1">
                    {getConfidenceIcon(field.confidence)}
                    {Math.round(field.confidence * 100)}%
                  </span>
                </Badge>
              )}
            </div>
            <div className="text-sm font-semibold">{field.value}</div>
            {field.confidence && field.confidence < 0.9 && (
              <p className="text-xs text-muted-foreground mt-1">
                {field.confidence < 0.7
                  ? 'Low confidence - please verify'
                  : 'Medium confidence - review recommended'}
              </p>
            )}
          </div>
        ))}
      </div>

      {invoice.line_items && invoice.line_items.length > 0 && (
        <div className="mt-6">
          <h4 className="font-semibold mb-3">Line Items ({invoice.line_items.length})</h4>
          <div className="space-y-2">
            {invoice.line_items.map((item, index) => (
              <div key={index} className="p-2 border rounded text-sm">
                <div className="flex justify-between mb-1">
                  <span className="font-medium">{item.description}</span>
                  <span className="font-semibold">
                    ${item.line_total?.toFixed(2) || '0.00'}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  Qty: {item.quantity || 0} × ${item.unit_price?.toFixed(2) || '0.00'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {invoice.risk_flags && invoice.risk_flags.length > 0 && (
        <div className="mt-6">
          <h4 className="font-semibold mb-3 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-destructive" />
            Risk Flags ({invoice.risk_flags.length})
          </h4>
          <div className="space-y-2">
            {invoice.risk_flags.map((flag, index) => (
              <div
                key={index}
                className="p-2 border border-destructive/30 rounded bg-destructive/5 text-sm"
              >
                <div className="flex items-center justify-between mb-1">
                  <Badge variant="destructive" className="text-xs">
                    {flag.severity}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {Math.round(flag.confidence * 100)}% confidence
                  </span>
                </div>
                <p className="font-medium">{flag.type}</p>
                <p className="text-xs text-muted-foreground mt-1">{flag.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
