"use client";

/**
 * ERP Sync Dashboard Component
 * 
 * Displays recent sync operations, statistics, and allows filtering of sync logs.
 */

import { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { erpApi, ERPConnection, ERPSyncLog } from '@/lib/api/erp';
import { useToast } from '@/hooks/use-toast';

interface ERPSyncDashboardProps {
  connections: ERPConnection[];
}

export function ERPSyncDashboard({ connections }: ERPSyncDashboardProps) {
  const [syncLogs, setSyncLogs] = useState<ERPSyncLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<string>('all');
  const [selectedEntityType, setSelectedEntityType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const { toast } = useToast();

  useEffect(() => {
    loadSyncLogs();
  }, [selectedConnection, selectedEntityType, selectedStatus]);

  const loadSyncLogs = async () => {
    try {
      setLoading(true);
      const params: any = {
        limit: 50,
        offset: 0,
      };

      if (selectedConnection !== 'all') {
        params.connection_id = selectedConnection;
      }
      if (selectedEntityType !== 'all') {
        params.entity_type = selectedEntityType;
      }
      if (selectedStatus !== 'all') {
        params.status = selectedStatus;
      }

      const logs = await erpApi.listSyncLogs(params);
      setSyncLogs(logs);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: 'Failed to load sync logs',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const getConnectionName = (connectionId: string) => {
    const conn = connections.find((c) => c.id === connectionId);
    return conn?.name || 'Unknown';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge className="bg-green-500">
            <CheckCircle className="w-3 h-3 mr-1" />
            Completed
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="destructive">
            <XCircle className="w-3 h-3 mr-1" />
            Failed
          </Badge>
        );
      case 'in_progress':
        return (
          <Badge className="bg-blue-500">
            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
            In Progress
          </Badge>
        );
      case 'partial':
        return (
          <Badge variant="secondary">
            <AlertCircle className="w-3 h-3 mr-1" />
            Partial
          </Badge>
        );
      case 'pending':
        return (
          <Badge variant="outline">
            <Clock className="w-3 h-3 mr-1" />
            Pending
          </Badge>
        );
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}m ${secs}s`;
  };

  const calculateStats = () => {
    const total = syncLogs.length;
    const completed = syncLogs.filter((log) => log.status === 'completed').length;
    const failed = syncLogs.filter((log) => log.status === 'failed').length;
    const inProgress = syncLogs.filter((log) => log.status === 'in_progress').length;

    const totalRecords = syncLogs.reduce((sum, log) => sum + log.total_count, 0);
    const successRecords = syncLogs.reduce((sum, log) => sum + log.success_count, 0);
    const errorRecords = syncLogs.reduce((sum, log) => sum + log.error_count, 0);

    return {
      total,
      completed,
      failed,
      inProgress,
      totalRecords,
      successRecords,
      errorRecords,
      successRate: totalRecords > 0 ? ((successRecords / totalRecords) * 100).toFixed(1) : '0',
    };
  };

  const stats = calculateStats();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Sync Statistics</CardTitle>
          <CardDescription>Overview of recent sync operations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl font-bold text-blue-600">{stats.total}</div>
              <div className="text-sm text-muted-foreground">Total Syncs</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">{stats.completed}</div>
              <div className="text-sm text-muted-foreground">Completed</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="text-3xl font-bold text-red-600">{stats.failed}</div>
              <div className="text-sm text-muted-foreground">Failed</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-3xl font-bold text-purple-600">{stats.successRate}%</div>
              <div className="text-sm text-muted-foreground">Success Rate</div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Records:</span>
              <span className="font-medium">{stats.totalRecords.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Successful:</span>
              <span className="font-medium text-green-600">{stats.successRecords.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Errors:</span>
              <span className="font-medium text-red-600">{stats.errorRecords.toLocaleString()}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Sync Logs</CardTitle>
              <CardDescription>Recent synchronization operations</CardDescription>
            </div>
            <Button onClick={loadSyncLogs} variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>

          <div className="flex gap-4 mt-4">
            <Select value={selectedConnection} onValueChange={setSelectedConnection}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Connections" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Connections</SelectItem>
                {connections.map((conn) => (
                  <SelectItem key={conn.id} value={conn.id}>
                    {conn.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedEntityType} onValueChange={setSelectedEntityType}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Entity Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="vendor">Vendors</SelectItem>
                <SelectItem value="purchase_order">Purchase Orders</SelectItem>
                <SelectItem value="invoice">Invoices</SelectItem>
                <SelectItem value="payment">Payments</SelectItem>
              </SelectContent>
            </Select>

            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="partial">Partial</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
              <p className="text-muted-foreground">Loading sync logs...</p>
            </div>
          ) : syncLogs.length === 0 ? (
            <div className="text-center py-8">
              <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">No sync logs found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Connection</TableHead>
                  <TableHead>Entity Type</TableHead>
                  <TableHead>Direction</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Records</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Started At</TableHead>
                  <TableHead>Triggered By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {syncLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-medium">{getConnectionName(log.connection_id)}</TableCell>
                    <TableCell className="capitalize">{log.entity_type.replace('_', ' ')}</TableCell>
                    <TableCell className="capitalize">{log.sync_direction}</TableCell>
                    <TableCell>{getStatusBadge(log.status)}</TableCell>
                    <TableCell className="text-right">
                      <div className="text-sm">
                        <div className="font-medium">{log.total_count}</div>
                        <div className="text-xs text-muted-foreground">
                          {log.success_count} OK, {log.error_count} errors
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{formatDuration(log.duration_seconds)}</TableCell>
                    <TableCell className="text-sm">{formatDate(log.started_at)}</TableCell>
                    <TableCell className="text-sm">{log.triggered_by}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
