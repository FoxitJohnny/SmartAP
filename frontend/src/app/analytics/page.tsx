'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import MetricCard from '@/components/analytics/metric-card';
import {
  InvoiceVolumeChart,
  StatusDistributionChart,
  ProcessingTimeChart,
  RiskDistributionChart,
  TopVendorsChart,
  STPRateChart,
} from '@/components/analytics/charts';
import {
  useDashboardMetrics,
  useInvoiceVolume,
  useStatusDistribution,
  useProcessingTimeData,
  useRiskDistribution,
  useTopVendors,
  useSTPRateData,
  useRecentActivity,
} from '@/lib/api/analytics';
import {
  TrendingUpIcon,
  DollarSignIcon,
  ClockIcon,
  AlertTriangleIcon,
  FileTextIcon,
  CheckCircleIcon,
  RefreshCwIcon,
  DownloadIcon,
  FilterIcon,
} from 'lucide-react';
import { format } from 'date-fns';

export default function AnalyticsPage() {
  const [dateRange] = useState({ startDate: '', endDate: '' });

  // Fetch all analytics data
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics(dateRange);
  const { data: invoiceVolume, isLoading: volumeLoading } = useInvoiceVolume(dateRange);
  const { data: statusDist, isLoading: statusLoading } = useStatusDistribution(dateRange);
  const { data: processingTime, isLoading: processingLoading } = useProcessingTimeData(dateRange);
  const { data: riskDist, isLoading: riskLoading } = useRiskDistribution(dateRange);
  const { data: topVendors, isLoading: vendorsLoading } = useTopVendors(10, dateRange);
  const { data: stpRate, isLoading: stpLoading } = useSTPRateData(dateRange);
  const { data: recentActivity, isLoading: activityLoading } = useRecentActivity(20);

  const isLoading =
    metricsLoading ||
    volumeLoading ||
    statusLoading ||
    processingLoading ||
    riskLoading ||
    vendorsLoading ||
    stpLoading ||
    activityLoading;

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'upload':
        return <FileTextIcon className="h-4 w-4" />;
      case 'approval':
        return <CheckCircleIcon className="h-4 w-4" />;
      case 'risk':
        return <AlertTriangleIcon className="h-4 w-4" />;
      case 'payment':
        return <DollarSignIcon className="h-4 w-4" />;
      case 'comment':
        return <FileTextIcon className="h-4 w-4" />;
      default:
        return <FileTextIcon className="h-4 w-4" />;
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'upload':
        return 'bg-blue-100 text-blue-700';
      case 'approval':
        return 'bg-green-100 text-green-700';
      case 'risk':
        return 'bg-red-100 text-red-700';
      case 'payment':
        return 'bg-purple-100 text-purple-700';
      case 'comment':
        return 'bg-gray-100 text-gray-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-screen">
          <RefreshCwIcon className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h2>
            <p className="text-muted-foreground">Real-time insights and performance metrics</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <FilterIcon className="h-4 w-4 mr-2" />
              Filter
            </Button>
            <Button variant="outline" size="sm">
              <DownloadIcon className="h-4 w-4 mr-2" />
              Export
            </Button>
            <Button variant="outline" size="sm">
              <RefreshCwIcon className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Key Metrics Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <MetricCard
            title="Total Invoices"
            value={metrics?.totalInvoices.value ?? 0}
            change={metrics?.totalInvoices.change}
            trend={metrics?.totalInvoices.trend}
            icon={FileTextIcon}
            format="number"
            description="from last period"
          />
          <MetricCard
            title="STP Rate"
            value={metrics?.stpRate.value ?? 0}
            change={metrics?.stpRate.change}
            trend={metrics?.stpRate.trend}
            icon={TrendingUpIcon}
            format="percentage"
            description="from last period"
          />
          <MetricCard
            title="Avg Processing Time"
            value={metrics?.avgProcessingTime.value ?? '0'}
            change={metrics?.avgProcessingTime.change}
            trend={metrics?.avgProcessingTime.trend}
            icon={ClockIcon}
            description="from last period"
          />
          <MetricCard
            title="Pending Approvals"
            value={metrics?.pendingApprovals.value ?? 0}
            change={metrics?.pendingApprovals.change}
            trend={metrics?.pendingApprovals.trend}
            icon={CheckCircleIcon}
            format="number"
            description="from last period"
          />
          <MetricCard
            title="Risk Flags"
            value={metrics?.riskFlags.value ?? 0}
            change={metrics?.riskFlags.change}
            trend={metrics?.riskFlags.trend}
            icon={AlertTriangleIcon}
            format="number"
            description="from last period"
          />
          <MetricCard
            title="Total Value"
            value={metrics?.totalValue.value ?? 0}
            change={metrics?.totalValue.change}
            trend={metrics?.totalValue.trend}
            icon={DollarSignIcon}
            format="currency"
            description="from last period"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left Column - Charts */}
          <div className="space-y-6">
            {invoiceVolume && <InvoiceVolumeChart data={invoiceVolume} />}
            {statusDist && <StatusDistributionChart data={statusDist} />}
            {processingTime && <ProcessingTimeChart data={processingTime} />}
          </div>

          {/* Right Column - Charts + Activity */}
          <div className="space-y-6">
            {riskDist && <RiskDistributionChart data={riskDist} />}
            {topVendors && <TopVendorsChart data={topVendors} />}

            {/* Recent Activity Feed */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Latest invoice processing events</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentActivity && recentActivity.length > 0 ? (
                    recentActivity.slice(0, 10).map((activity) => (
                      <div key={activity.id} className="flex items-start gap-3">
                        <div
                          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${getActivityColor(
                            activity.type
                          )}`}
                        >
                          {getActivityIcon(activity.type)}
                        </div>
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium leading-none">
                            {activity.description}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>Invoice #{activity.invoiceNumber}</span>
                            <span>•</span>
                            <span>{activity.user}</span>
                            <span>•</span>
                            <span>{format(new Date(activity.timestamp), 'MMM d, h:mm a')}</span>
                          </div>
                        </div>
                        {activity.status && (
                          <div className="text-xs font-medium text-muted-foreground">
                            {activity.status}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="flex items-center justify-center py-8 text-muted-foreground">
                      <p>No recent activity</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Bottom Row - Full Width Chart */}
        {stpRate && <STPRateChart data={stpRate} />}
      </div>
    </DashboardLayout>
  );
}
