'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// Color palette
const COLORS = {
  primary: '#0ea5e9',
  secondary: '#8b5cf6',
  success: '#22c55e',
  warning: '#eab308',
  danger: '#ef4444',
  neutral: '#6b7280',
};

const STATUS_COLORS = ['#0ea5e9', '#22c55e', '#eab308', '#ef4444', '#8b5cf6', '#6b7280'];
const RISK_COLORS = ['#ef4444', '#eab308', '#22c55e', '#6b7280'];

// Invoice Volume Line Chart
interface InvoiceVolumeChartProps {
  data: Array<{ date: string; count: number; value: number }>;
}

export function InvoiceVolumeChart({ data }: InvoiceVolumeChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Invoice Volume Over Time</CardTitle>
        <CardDescription>Number and value of invoices processed</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="count"
              stroke={COLORS.primary}
              strokeWidth={2}
              name="Invoice Count"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="value"
              stroke={COLORS.success}
              strokeWidth={2}
              name="Total Value"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// Status Distribution Pie Chart
interface StatusDistributionChartProps {
  data: Array<{ status: string; count: number; percentage: number }>;
}

export function StatusDistributionChart({ data }: StatusDistributionChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Status Distribution</CardTitle>
        <CardDescription>Breakdown of invoices by status</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              outerRadius={100}
              fill={COLORS.primary}
              dataKey="count"
              nameKey="status"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={STATUS_COLORS[index % STATUS_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// Processing Time Trend Area Chart
interface ProcessingTimeChartProps {
  data: Array<{ date: string; avgTime: number; minTime: number; maxTime: number }>;
}

export function ProcessingTimeChart({ data }: ProcessingTimeChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Time Trends</CardTitle>
        <CardDescription>Average, min, and max processing times</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Area
              type="monotone"
              dataKey="maxTime"
              stackId="1"
              stroke={COLORS.danger}
              fill={COLORS.danger}
              fillOpacity={0.2}
              name="Max Time"
            />
            <Area
              type="monotone"
              dataKey="avgTime"
              stackId="2"
              stroke={COLORS.primary}
              fill={COLORS.primary}
              fillOpacity={0.4}
              name="Avg Time"
            />
            <Area
              type="monotone"
              dataKey="minTime"
              stackId="3"
              stroke={COLORS.success}
              fill={COLORS.success}
              fillOpacity={0.6}
              name="Min Time"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// Risk Distribution Bar Chart
interface RiskDistributionChartProps {
  data: Array<{ riskLevel: string; count: number; percentage: number }>;
}

export function RiskDistributionChart({ data }: RiskDistributionChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Level Distribution</CardTitle>
        <CardDescription>Invoices by risk classification</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="riskLevel" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" name="Invoice Count">
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={RISK_COLORS[index % RISK_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// Top Vendors Horizontal Bar Chart
interface TopVendorsChartProps {
  data: Array<{ vendorName: string; invoiceCount: number; totalAmount: number }>;
}

export function TopVendorsChart({ data }: TopVendorsChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Vendors by Volume</CardTitle>
        <CardDescription>Highest invoice volumes by vendor</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="vendorName" type="category" width={150} />
            <Tooltip />
            <Legend />
            <Bar dataKey="invoiceCount" fill={COLORS.primary} name="Invoice Count" />
            <Bar dataKey="totalAmount" fill={COLORS.success} name="Total Amount" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// STP Rate Trend Line Chart
interface STPRateChartProps {
  data: Array<{ week: string; rate: number; processed: number; touchless: number }>;
}

export function STPRateChart({ data }: STPRateChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Straight-Through Processing (STP) Rate</CardTitle>
        <CardDescription>Weekly STP rate and processing volume</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="week" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="rate"
              stroke={COLORS.success}
              strokeWidth={3}
              name="STP Rate (%)"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="processed"
              stroke={COLORS.primary}
              strokeWidth={2}
              name="Processed"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="touchless"
              stroke={COLORS.secondary}
              strokeWidth={2}
              name="Touchless"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
