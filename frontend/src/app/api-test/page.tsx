'use client';

/**
 * API Integration Test Page
 * Phase 4.1: Backend Integration & Testing
 * 
 * This page provides tools to test API connectivity and validate
 * all backend integrations before deploying to production.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  testAPIConnection, 
  testAPIEndpoints, 
  getAPIConfig, 
  type APITestResult 
} from '@/lib/api/test-utils';

export default function APITestPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [healthResult, setHealthResult] = useState<APITestResult | null>(null);
  const [endpointResults, setEndpointResults] = useState<APITestResult[]>([]);

  const config = getAPIConfig();

  const handleTestHealth = async () => {
    setIsLoading(true);
    try {
      const result = await testAPIConnection();
      setHealthResult(result);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestAllEndpoints = async () => {
    setIsLoading(true);
    try {
      const endpoints = [
        '/health',
        '/invoices',
        '/approvals',
        '/analytics/metrics',
        '/purchase-orders',
        '/vendors',
      ];
      
      const results = await testAPIEndpoints(endpoints);
      setEndpointResults(results);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return <Badge className="bg-green-500">Success</Badge>;
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      case 'timeout':
        return <Badge variant="secondary">Timeout</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">API Integration Testing</h1>
        <p className="text-muted-foreground mt-2">
          Test backend API connectivity and validate all integrations (Phase 4.1)
        </p>
      </div>

      {/* Configuration Info */}
      <Card>
        <CardHeader>
          <CardTitle>API Configuration</CardTitle>
          <CardDescription>Current environment and API settings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Base URL</p>
              <p className="font-mono text-sm">{config.baseURL}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Environment</p>
              <p className="text-sm">{config.environment}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Timeout</p>
              <p className="text-sm">{config.timeout}ms</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Mock Data</p>
              <p className="text-sm">{config.enableMockData ? 'Enabled' : 'Disabled'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Health Check */}
      <Card>
        <CardHeader>
          <CardTitle>Health Check</CardTitle>
          <CardDescription>Test basic API connectivity</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={handleTestHealth} disabled={isLoading}>
            {isLoading ? 'Testing...' : 'Test Health Endpoint'}
          </Button>

          {healthResult && (
            <div className="border rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">{healthResult.endpoint}</span>
                {getStatusBadge(healthResult.status)}
              </div>
              
              {healthResult.statusCode && (
                <p className="text-sm text-muted-foreground">
                  Status Code: {healthResult.statusCode}
                </p>
              )}
              
              {healthResult.responseTime && (
                <p className="text-sm text-muted-foreground">
                  Response Time: {healthResult.responseTime}ms
                </p>
              )}
              
              {healthResult.error && (
                <p className="text-sm text-red-600">Error: {healthResult.error}</p>
              )}
              
              {healthResult.data && typeof healthResult.data === 'object' ? (
                <div className="bg-muted p-2 rounded">
                  <pre className="text-xs overflow-auto">
                    {JSON.stringify(healthResult.data, null, 2)}
                  </pre>
                </div>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>

      {/* All Endpoints Test */}
      <Card>
        <CardHeader>
          <CardTitle>Endpoint Integration Tests</CardTitle>
          <CardDescription>Test all major API endpoints</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={handleTestAllEndpoints} disabled={isLoading}>
            {isLoading ? 'Testing...' : 'Test All Endpoints'}
          </Button>

          {endpointResults.length > 0 && (
            <div className="space-y-2">
              {endpointResults.map((result, index) => (
                <div key={index} className="border rounded-lg p-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm">{result.endpoint}</span>
                    <div className="flex items-center gap-2">
                      {result.responseTime && (
                        <span className="text-xs text-muted-foreground">
                          {result.responseTime}ms
                        </span>
                      )}
                      {getStatusBadge(result.status)}
                    </div>
                  </div>
                  
                  {result.error && (
                    <p className="text-xs text-red-600">{result.error}</p>
                  )}
                </div>
              ))}

              {/* Summary */}
              <div className="border-t pt-4 mt-4">
                <p className="text-sm font-medium">Summary:</p>
                <div className="grid grid-cols-3 gap-4 mt-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Success Rate</p>
                    <p className="text-lg font-bold">
                      {((endpointResults.filter((r) => r.status === 'success').length / endpointResults.length) * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Avg Response Time</p>
                    <p className="text-lg font-bold">
                      {(endpointResults.reduce((sum, r) => sum + (r.responseTime || 0), 0) / endpointResults.length).toFixed(0)}ms
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Total Tests</p>
                    <p className="text-lg font-bold">{endpointResults.length}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
