/**
 * API Integration Test Utilities
 * Phase 4.1: Backend Integration & Testing
 * 
 * Utilities for testing API connectivity and validating responses
 */

import { apiClient } from './client';

export interface APITestResult {
  endpoint: string;
  status: 'success' | 'error' | 'timeout';
  statusCode?: number;
  responseTime?: number;
  error?: string;
  data?: unknown;
}

/**
 * Test API connectivity to backend
 */
export async function testAPIConnection(): Promise<APITestResult> {
  const startTime = Date.now();
  
  try {
    const response = await apiClient.get('/health');
    const responseTime = Date.now() - startTime;
    
    return {
      endpoint: '/health',
      status: 'success',
      statusCode: response.status,
      responseTime,
      data: response.data,
    };
  } catch (error: unknown) {
    const responseTime = Date.now() - startTime;
    
    if (error instanceof Error) {
      return {
        endpoint: '/health',
        status: error.message.includes('timeout') ? 'timeout' : 'error',
        responseTime,
        error: error.message,
      };
    }
    
    return {
      endpoint: '/health',
      status: 'error',
      responseTime,
      error: 'Unknown error occurred',
    };
  }
}

/**
 * Test multiple API endpoints
 */
export async function testAPIEndpoints(endpoints: string[]): Promise<APITestResult[]> {
  const results: APITestResult[] = [];
  
  for (const endpoint of endpoints) {
    const startTime = Date.now();
    
    try {
      const response = await apiClient.get(endpoint);
      const responseTime = Date.now() - startTime;
      
      results.push({
        endpoint,
        status: 'success',
        statusCode: response.status,
        responseTime,
        data: response.data,
      });
    } catch (error: unknown) {
      const responseTime = Date.now() - startTime;
      
      if (error instanceof Error) {
        results.push({
          endpoint,
          status: error.message.includes('timeout') ? 'timeout' : 'error',
          responseTime,
          error: error.message,
        });
      } else {
        results.push({
          endpoint,
          status: 'error',
          responseTime,
          error: 'Unknown error occurred',
        });
      }
    }
  }
  
  return results;
}

/**
 * Test authentication flow
 */
export async function testAuthFlow(username: string, password: string): Promise<APITestResult> {
  const startTime = Date.now();
  
  try {
    const response = await apiClient.post('/auth/login', {
      username,
      password,
    });
    
    const responseTime = Date.now() - startTime;
    
    // Store tokens if successful
    if (response.data.access_token) {
      const tokenKey = process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY || 'auth_token';
      const refreshTokenKey = process.env.NEXT_PUBLIC_REFRESH_TOKEN_KEY || 'refresh_token';
      
      localStorage.setItem(tokenKey, response.data.access_token);
      
      if (response.data.refresh_token) {
        localStorage.setItem(refreshTokenKey, response.data.refresh_token);
      }
    }
    
    return {
      endpoint: '/auth/login',
      status: 'success',
      statusCode: response.status,
      responseTime,
      data: { hasToken: !!response.data.access_token },
    };
  } catch (error: unknown) {
    const responseTime = Date.now() - startTime;
    
    if (error instanceof Error) {
      return {
        endpoint: '/auth/login',
        status: 'error',
        responseTime,
        error: error.message,
      };
    }
    
    return {
      endpoint: '/auth/login',
      status: 'error',
      responseTime,
      error: 'Authentication failed',
    };
  }
}

/**
 * Get API configuration info
 */
export function getAPIConfig() {
  return {
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    timeout: Number(process.env.NEXT_PUBLIC_API_TIMEOUT) || 30000,
    enableMockData: process.env.NEXT_PUBLIC_ENABLE_MOCK_DATA === 'true',
    enableDebugLogs: process.env.NEXT_PUBLIC_ENABLE_DEBUG_LOGS === 'true',
    environment: process.env.NEXT_PUBLIC_ENV || 'development',
  };
}

/**
 * Log API test results
 */
export function logAPITestResults(results: APITestResult | APITestResult[]) {
  const resultsArray = Array.isArray(results) ? results : [results];
  
  console.group('🔧 API Integration Test Results');
  
  resultsArray.forEach((result) => {
    const icon = result.status === 'success' ? '✅' : '❌';
    const timeStr = result.responseTime ? `${result.responseTime}ms` : 'N/A';
    
    console.log(`${icon} ${result.endpoint}`, {
      status: result.status,
      statusCode: result.statusCode,
      responseTime: timeStr,
      error: result.error,
    });
  });
  
  console.groupEnd();
  
  // Summary
  const successCount = resultsArray.filter((r) => r.status === 'success').length;
  const totalCount = resultsArray.length;
  const avgResponseTime =
    resultsArray.reduce((sum, r) => sum + (r.responseTime || 0), 0) / totalCount;
  
  console.log('📊 Summary:', {
    success: `${successCount}/${totalCount}`,
    successRate: `${((successCount / totalCount) * 100).toFixed(1)}%`,
    avgResponseTime: `${avgResponseTime.toFixed(0)}ms`,
  });
}
