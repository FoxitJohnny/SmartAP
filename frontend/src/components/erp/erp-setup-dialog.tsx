"use client";

/**
 * ERP Setup Dialog Component
 * 
 * Multi-step wizard for creating or editing ERP connections.
 * Handles different authentication methods for various ERP systems.
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { erpApi, ERPConnection, ERPConnectionCreate } from '@/lib/api/erp';
import { useToast } from '@/hooks/use-toast';
import { Loader2, CheckCircle } from 'lucide-react';

interface ERPSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connection?: ERPConnection | null;
  onSuccess: () => void;
}

type ERPSystem = 'quickbooks' | 'xero' | 'sap' | 'sage' | 'netsuite' | 'oracle' | 'dynamics';

export function ERPSetupDialog({ open, onOpenChange, connection, onSuccess }: ERPSetupDialogProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    name: '',
    system_type: '' as ERPSystem | '',
    auto_sync_enabled: true,
    sync_interval_minutes: 60,
    // QuickBooks fields
    qb_client_id: '',
    qb_client_secret: '',
    qb_realm_id: '',
    qb_access_token: '',
    qb_refresh_token: '',
    // Xero fields
    xero_client_id: '',
    xero_client_secret: '',
    xero_tenant_id: '',
    xero_access_token: '',
    xero_refresh_token: '',
    // SAP fields
    sap_service_layer_url: '',
    sap_company_db: '',
    sap_username: '',
    sap_password: '',
    // NetSuite fields
    ns_account_id: '',
    ns_consumer_key: '',
    ns_consumer_secret: '',
    ns_token_id: '',
    ns_token_secret: '',
    ns_restlet_url: '',
  });

  useEffect(() => {
    if (connection) {
      setFormData({
        name: connection.name,
        system_type: connection.system_type as ERPSystem,
        auto_sync_enabled: connection.auto_sync_enabled,
        sync_interval_minutes: connection.sync_interval_minutes,
        qb_client_id: '',
        qb_client_secret: '',
        qb_realm_id: '',
        qb_access_token: '',
        qb_refresh_token: '',
        xero_client_id: '',
        xero_client_secret: '',
        xero_tenant_id: connection.tenant_id || '',
        xero_access_token: '',
        xero_refresh_token: '',
        sap_service_layer_url: connection.api_url || '',
        sap_company_db: connection.company_db || '',
        sap_username: '',
        sap_password: '',
        ns_account_id: '',
        ns_consumer_key: '',
        ns_consumer_secret: '',
        ns_token_id: '',
        ns_token_secret: '',
        ns_restlet_url: connection.api_url || '',
      });
    } else {
      resetForm();
    }
  }, [connection, open]);

  const resetForm = () => {
    setFormData({
      name: '',
      system_type: '',
      auto_sync_enabled: true,
      sync_interval_minutes: 60,
      qb_client_id: '',
      qb_client_secret: '',
      qb_realm_id: '',
      qb_access_token: '',
      qb_refresh_token: '',
      xero_client_id: '',
      xero_client_secret: '',
      xero_tenant_id: '',
      xero_access_token: '',
      xero_refresh_token: '',
      sap_service_layer_url: '',
      sap_company_db: '',
      sap_username: '',
      sap_password: '',
      ns_account_id: '',
      ns_consumer_key: '',
      ns_consumer_secret: '',
      ns_token_id: '',
      ns_token_secret: '',
      ns_restlet_url: '',
    });
    setStep(1);
    setTestResult(null);
  };

  const buildCredentials = () => {
    if (formData.system_type === 'quickbooks') {
      return {
        client_id: formData.qb_client_id,
        client_secret: formData.qb_client_secret,
        realm_id: formData.qb_realm_id,
        access_token: formData.qb_access_token,
        refresh_token: formData.qb_refresh_token,
      };
    } else if (formData.system_type === 'xero') {
      return {
        client_id: formData.xero_client_id,
        client_secret: formData.xero_client_secret,
        tenant_id: formData.xero_tenant_id,
        access_token: formData.xero_access_token,
        refresh_token: formData.xero_refresh_token,
      };
    } else if (formData.system_type === 'sap') {
      return {
        service_layer_url: formData.sap_service_layer_url,
        company_db: formData.sap_company_db,
        username: formData.sap_username,
        password: formData.sap_password,
      };
    } else if (formData.system_type === 'netsuite') {
      return {
        account_id: formData.ns_account_id,
        consumer_key: formData.ns_consumer_key,
        consumer_secret: formData.ns_consumer_secret,
        token_id: formData.ns_token_id,
        token_secret: formData.ns_token_secret,
        restlet_url: formData.ns_restlet_url,
      };
    }
    return {};
  };

  const handleTestConnection = async () => {
    setLoading(true);
    setTestResult(null);

    try {
      // First create/update the connection
      const connectionData: ERPConnectionCreate = {
        name: formData.name,
        system_type: formData.system_type!,
        credentials: buildCredentials(),
        tenant_id: formData.system_type === 'xero' ? formData.xero_tenant_id : undefined,
        company_db: formData.system_type === 'sap' ? formData.sap_company_db : undefined,
        api_url: formData.system_type === 'sap' ? formData.sap_service_layer_url : 
                formData.system_type === 'netsuite' ? formData.ns_restlet_url : undefined,
        auto_sync_enabled: formData.auto_sync_enabled,
        sync_interval_minutes: formData.sync_interval_minutes,
      };

      let connectionId: string;
      if (connection) {
        const updated = await erpApi.updateConnection(connection.id, connectionData);
        connectionId = updated.id;
      } else {
        const created = await erpApi.createConnection(connectionData);
        connectionId = created.id;
      }

      // Test the connection
      const result = await erpApi.testConnection(connectionId);
      setTestResult(result);

      toast({
        title: 'Connection successful!',
        description: `Connected to ${result.company_name}`,
      });
    } catch (error: any) {
      toast({
        title: 'Connection failed',
        description: error.response?.data?.detail || 'Failed to connect to ERP system',
        variant: 'destructive',
      });
      setTestResult({ success: false, error: error.response?.data?.detail });
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = () => {
    onSuccess();
    resetForm();
  };

  const renderStep1 = () => (
    <div className="space-y-4">
      <div>
        <Label htmlFor="name">Connection Name</Label>
        <Input
          id="name"
          placeholder="e.g., QuickBooks Production"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        />
      </div>

      <div>
        <Label htmlFor="system_type">ERP System</Label>
        <Select
          value={formData.system_type}
          onValueChange={(value) => setFormData({ ...formData, system_type: value as ERPSystem })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select ERP system" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="quickbooks">QuickBooks Online</SelectItem>
            <SelectItem value="xero">Xero</SelectItem>
            <SelectItem value="sap">SAP Business One / S/4HANA</SelectItem>
            <SelectItem value="netsuite">NetSuite</SelectItem>
            <SelectItem value="sage">Sage (Coming Soon)</SelectItem>
            <SelectItem value="oracle">Oracle (Coming Soon)</SelectItem>
            <SelectItem value="dynamics">Microsoft Dynamics (Coming Soon)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button
        onClick={() => setStep(2)}
        disabled={!formData.name || !formData.system_type}
        className="w-full"
      >
        Next: Authentication
      </Button>
    </div>
  );

  const renderStep2 = () => {
    if (formData.system_type === 'quickbooks') {
      return (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">QuickBooks Online Authentication</h3>
          <div className="text-sm text-muted-foreground mb-4">
            Get your OAuth credentials from the QuickBooks Developer Portal
          </div>

          <div>
            <Label htmlFor="qb_client_id">Client ID</Label>
            <Input
              id="qb_client_id"
              value={formData.qb_client_id}
              onChange={(e) => setFormData({ ...formData, qb_client_id: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="qb_client_secret">Client Secret</Label>
            <Input
              id="qb_client_secret"
              type="password"
              value={formData.qb_client_secret}
              onChange={(e) => setFormData({ ...formData, qb_client_secret: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="qb_realm_id">Realm ID (Company ID)</Label>
            <Input
              id="qb_realm_id"
              value={formData.qb_realm_id}
              onChange={(e) => setFormData({ ...formData, qb_realm_id: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="qb_access_token">Access Token</Label>
            <Input
              id="qb_access_token"
              value={formData.qb_access_token}
              onChange={(e) => setFormData({ ...formData, qb_access_token: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="qb_refresh_token">Refresh Token</Label>
            <Input
              id="qb_refresh_token"
              value={formData.qb_refresh_token}
              onChange={(e) => setFormData({ ...formData, qb_refresh_token: e.target.value })}
            />
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
              Back
            </Button>
            <Button onClick={() => setStep(3)} className="flex-1">
              Next: Test Connection
            </Button>
          </div>
        </div>
      );
    }

    if (formData.system_type === 'xero') {
      return (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Xero Authentication</h3>
          <div className="text-sm text-muted-foreground mb-4">
            Get your OAuth credentials from the Xero Developer Portal
          </div>

          <div>
            <Label htmlFor="xero_client_id">Client ID</Label>
            <Input
              id="xero_client_id"
              value={formData.xero_client_id}
              onChange={(e) => setFormData({ ...formData, xero_client_id: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="xero_client_secret">Client Secret</Label>
            <Input
              id="xero_client_secret"
              type="password"
              value={formData.xero_client_secret}
              onChange={(e) => setFormData({ ...formData, xero_client_secret: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="xero_tenant_id">Tenant ID (Organization ID)</Label>
            <Input
              id="xero_tenant_id"
              value={formData.xero_tenant_id}
              onChange={(e) => setFormData({ ...formData, xero_tenant_id: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="xero_access_token">Access Token</Label>
            <Input
              id="xero_access_token"
              value={formData.xero_access_token}
              onChange={(e) => setFormData({ ...formData, xero_access_token: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="xero_refresh_token">Refresh Token</Label>
            <Input
              id="xero_refresh_token"
              value={formData.xero_refresh_token}
              onChange={(e) => setFormData({ ...formData, xero_refresh_token: e.target.value })}
            />
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
              Back
            </Button>
            <Button onClick={() => setStep(3)} className="flex-1">
              Next: Test Connection
            </Button>
          </div>
        </div>
      );
    }

    if (formData.system_type === 'sap') {
      return (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">SAP Business One Authentication</h3>
          <div className="text-sm text-muted-foreground mb-4">
            Enter your SAP Service Layer credentials
          </div>

          <div>
            <Label htmlFor="sap_service_layer_url">Service Layer URL</Label>
            <Input
              id="sap_service_layer_url"
              placeholder="https://your-sap-server:50000"
              value={formData.sap_service_layer_url}
              onChange={(e) => setFormData({ ...formData, sap_service_layer_url: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="sap_company_db">Company Database</Label>
            <Input
              id="sap_company_db"
              placeholder="SBODEMOUS"
              value={formData.sap_company_db}
              onChange={(e) => setFormData({ ...formData, sap_company_db: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="sap_username">Username</Label>
            <Input
              id="sap_username"
              value={formData.sap_username}
              onChange={(e) => setFormData({ ...formData, sap_username: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="sap_password">Password</Label>
            <Input
              id="sap_password"
              type="password"
              value={formData.sap_password}
              onChange={(e) => setFormData({ ...formData, sap_password: e.target.value })}
            />
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
              Back
            </Button>
            <Button onClick={() => setStep(3)} className="flex-1">
              Next: Test Connection
            </Button>
          </div>
        </div>
      );
    }

    if (formData.system_type === 'netsuite') {
      return (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">NetSuite Token-Based Authentication</h3>
          <div className="text-sm text-muted-foreground mb-4">
            Configure Token-Based Authentication (TBA) in your NetSuite account and deploy the required RESTlets
          </div>

          <div>
            <Label htmlFor="ns_account_id">Account ID</Label>
            <Input
              id="ns_account_id"
              placeholder="1234567"
              value={formData.ns_account_id}
              onChange={(e) => setFormData({ ...formData, ns_account_id: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="ns_consumer_key">Consumer Key</Label>
            <Input
              id="ns_consumer_key"
              value={formData.ns_consumer_key}
              onChange={(e) => setFormData({ ...formData, ns_consumer_key: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="ns_consumer_secret">Consumer Secret</Label>
            <Input
              id="ns_consumer_secret"
              type="password"
              value={formData.ns_consumer_secret}
              onChange={(e) => setFormData({ ...formData, ns_consumer_secret: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="ns_token_id">Token ID</Label>
            <Input
              id="ns_token_id"
              value={formData.ns_token_id}
              onChange={(e) => setFormData({ ...formData, ns_token_id: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="ns_token_secret">Token Secret</Label>
            <Input
              id="ns_token_secret"
              type="password"
              value={formData.ns_token_secret}
              onChange={(e) => setFormData({ ...formData, ns_token_secret: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="ns_restlet_url">RESTlet Base URL</Label>
            <Input
              id="ns_restlet_url"
              placeholder="https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl"
              value={formData.ns_restlet_url}
              onChange={(e) => setFormData({ ...formData, ns_restlet_url: e.target.value })}
            />
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
              Back
            </Button>
            <Button onClick={() => setStep(3)} className="flex-1">
              Next: Test Connection
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Coming soon...</p>
        <Button variant="outline" onClick={() => setStep(1)} className="mt-4">
          Back
        </Button>
      </div>
    );
  };

  const renderStep3 = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Test Connection</h3>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label htmlFor="auto_sync">Enable Auto Sync</Label>
          <Switch
            id="auto_sync"
            checked={formData.auto_sync_enabled}
            onCheckedChange={(checked) => setFormData({ ...formData, auto_sync_enabled: checked })}
          />
        </div>

        {formData.auto_sync_enabled && (
          <div>
            <Label htmlFor="sync_interval">Sync Interval (minutes)</Label>
            <Input
              id="sync_interval"
              type="number"
              min="5"
              max="1440"
              value={formData.sync_interval_minutes}
              onChange={(e) =>
                setFormData({ ...formData, sync_interval_minutes: parseInt(e.target.value) || 60 })
              }
            />
          </div>
        )}
      </div>

      {testResult && (
        <div
          className={`p-4 rounded-md ${
            testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
          }`}
        >
          {testResult.success ? (
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <div>
                <p className="font-semibold text-green-900">Connection Successful!</p>
                <p className="text-sm text-green-700">Connected to {testResult.company_name}</p>
              </div>
            </div>
          ) : (
            <div>
              <p className="font-semibold text-red-900">Connection Failed</p>
              <p className="text-sm text-red-700">{testResult.error}</p>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setStep(2)} className="flex-1">
          Back
        </Button>
        <Button onClick={handleTestConnection} disabled={loading} className="flex-1">
          {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
          Test Connection
        </Button>
      </div>

      {testResult?.success && (
        <Button onClick={handleComplete} className="w-full">
          Complete Setup
        </Button>
      )}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {connection ? 'Edit ERP Connection' : 'Add ERP Connection'}
          </DialogTitle>
          <DialogDescription>
            Step {step} of 3: {step === 1 ? 'Basic Info' : step === 2 ? 'Authentication' : 'Test & Configure'}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {step === 1 && renderStep1()}
          {step === 2 && renderStep2()}
          {step === 3 && renderStep3()}
        </div>
      </DialogContent>
    </Dialog>
  );
}
