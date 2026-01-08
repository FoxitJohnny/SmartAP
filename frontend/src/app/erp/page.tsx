"use client";

/**
 * ERP Connections Management Page
 * 
 * Main page for managing ERP system connections, viewing sync status,
 * and accessing ERP integration settings.
 */

import { useState, useEffect } from 'react';
import { Plus, RefreshCw, Trash2, Edit, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { erpApi, ERPConnection } from '@/lib/api/erp';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { ERPSetupDialog } from '@/components/erp/erp-setup-dialog';
import { ERPSyncDashboard } from '@/components/erp/erp-sync-dashboard';

export default function ERPConnectionsPage() {
  const [connections, setConnections] = useState<ERPConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [setupDialogOpen, setSetupDialogOpen] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<ERPConnection | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      setLoading(true);
      const data = await erpApi.listConnections();
      setConnections(data);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to load ERP connections',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (connectionId: string) => {
    try {
      toast({
        title: 'Testing connection...',
        description: 'Please wait while we test the connection',
      });

      const result = await erpApi.testConnection(connectionId);

      if (result.success) {
        toast({
          title: 'Connection successful',
          description: `Connected to ${result.company_name}`,
        });
        loadConnections(); // Refresh to show updated status
      }
    } catch (error: any) {
      toast({
        title: 'Connection failed',
        description: error.response?.data?.detail || 'Failed to test connection',
        variant: 'destructive',
      });
    }
  };

  const handleSyncVendors = async (connectionId: string) => {
    try {
      toast({
        title: 'Syncing vendors...',
        description: 'Vendor sync has been started',
      });

      await erpApi.syncVendors(connectionId);

      toast({
        title: 'Sync started',
        description: 'Vendor sync is running in the background',
      });
    } catch (error: any) {
      toast({
        title: 'Sync failed',
        description: error.response?.data?.detail || 'Failed to start vendor sync',
        variant: 'destructive',
      });
    }
  };

  const handleSyncPurchaseOrders = async (connectionId: string) => {
    try {
      toast({
        title: 'Syncing purchase orders...',
        description: 'Purchase order sync has been started',
      });

      await erpApi.syncPurchaseOrders(connectionId);

      toast({
        title: 'Sync started',
        description: 'Purchase order sync is running in the background',
      });
    } catch (error: any) {
      toast({
        title: 'Sync failed',
        description: error.response?.data?.detail || 'Failed to start purchase order sync',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteConnection = async (connectionId: string) => {
    if (!confirm('Are you sure you want to delete this connection? This will also delete all sync logs and mappings.')) {
      return;
    }

    try {
      await erpApi.deleteConnection(connectionId);
      toast({
        title: 'Connection deleted',
        description: 'ERP connection has been deleted successfully',
      });
      loadConnections();
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete connection',
        variant: 'destructive',
      });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" />Active</Badge>;
      case 'error':
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" />Error</Badge>;
      case 'pending':
        return <Badge variant="secondary"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
      case 'inactive':
        return <Badge variant="outline"><AlertCircle className="w-3 h-3 mr-1" />Inactive</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getSystemName = (systemType: string) => {
    const names: Record<string, string> = {
      quickbooks: 'QuickBooks Online',
      xero: 'Xero',
      sap: 'SAP Business One',
      sage: 'Sage',
      netsuite: 'NetSuite',
      oracle: 'Oracle',
      dynamics: 'Microsoft Dynamics',
    };
    return names[systemType] || systemType;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">ERP Integrations</h1>
          <p className="text-muted-foreground mt-2">
            Manage connections to external ERP systems for automated data sync
          </p>
        </div>
        <Button onClick={() => setSetupDialogOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Connection
        </Button>
      </div>

      {/* Connection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full text-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">Loading connections...</p>
          </div>
        ) : connections.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No ERP connections</h3>
            <p className="text-muted-foreground mb-4">
              Get started by adding your first ERP connection
            </p>
            <Button onClick={() => setSetupDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Connection
            </Button>
          </div>
        ) : (
          connections.map((connection) => (
            <Card key={connection.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{connection.name}</CardTitle>
                    <CardDescription>{getSystemName(connection.system_type)}</CardDescription>
                  </div>
                  {getStatusBadge(connection.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-sm space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Connected:</span>
                    <span className="font-medium">{formatDate(connection.last_connected_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Sync:</span>
                    <span className="font-medium">{formatDate(connection.last_sync_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Auto Sync:</span>
                    <span className="font-medium">
                      {connection.auto_sync_enabled ? `Every ${connection.sync_interval_minutes} min` : 'Disabled'}
                    </span>
                  </div>
                </div>

                {connection.connection_error && (
                  <div className="bg-destructive/10 border border-destructive/20 rounded-md p-3">
                    <p className="text-sm text-destructive">
                      <strong>Error:</strong> {connection.connection_error}
                    </p>
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleTestConnection(connection.id)}
                  >
                    Test Connection
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSyncVendors(connection.id)}
                  >
                    Sync Vendors
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSyncPurchaseOrders(connection.id)}
                  >
                    Sync POs
                  </Button>
                </div>

                <div className="flex gap-2 pt-2 border-t">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setSelectedConnection(connection);
                      setSetupDialogOpen(true);
                    }}
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive hover:text-destructive"
                    onClick={() => handleDeleteConnection(connection.id)}
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Sync Dashboard */}
      {connections.length > 0 && (
        <ERPSyncDashboard connections={connections} />
      )}

      {/* Setup Dialog */}
      <ERPSetupDialog
        open={setupDialogOpen}
        onOpenChange={(open) => {
          setSetupDialogOpen(open);
          if (!open) {
            setSelectedConnection(null);
          }
        }}
        connection={selectedConnection}
        onSuccess={() => {
          loadConnections();
          setSetupDialogOpen(false);
          setSelectedConnection(null);
        }}
      />
    </div>
  );
}
