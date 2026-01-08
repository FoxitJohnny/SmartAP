/**
 * API Client Configuration
 * 
 * Axios instance with request/response interceptors for authentication,
 * error handling, and request transformation.
 * 
 * Phase 4.1: Enhanced for backend integration testing
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

// API configuration from environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const API_TIMEOUT = Number(process.env.NEXT_PUBLIC_API_TIMEOUT) || 30000;
const ENABLE_DEBUG_LOGS = process.env.NEXT_PUBLIC_ENABLE_DEBUG_LOGS === 'true';

// Log configuration in development
if (process.env.NODE_ENV === 'development' && ENABLE_DEBUG_LOGS) {
  console.log('[API Client] Configuration:', {
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    env: process.env.NODE_ENV,
  });
}

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request Interceptor
 * Adds authentication token to requests and logs in debug mode
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const tokenKey = process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY || 'auth_token';
    
    // Get token from localStorage
    const token = typeof window !== 'undefined' ? localStorage.getItem(tokenKey) : null;
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Log request in debug mode
    if (ENABLE_DEBUG_LOGS) {
      console.log('[API Request]', {
        method: config.method?.toUpperCase(),
        url: config.url,
        hasAuth: !!token,
      });
    }
    
    return config;
  },
  (error: AxiosError) => {
    if (ENABLE_DEBUG_LOGS) {
      console.error('[API Request Error]', error);
    }
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 * Handles authentication errors, token refresh, and logs responses
 */
apiClient.interceptors.response.use(
  (response) => {
    // Log response in debug mode
    if (ENABLE_DEBUG_LOGS) {
      console.log('[API Response]', {
        status: response.status,
        url: response.config.url,
        data: response.data,
      });
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    
    const tokenKey = process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY || 'auth_token';
    const refreshTokenKey = process.env.NEXT_PUBLIC_REFRESH_TOKEN_KEY || 'refresh_token';

    // Log error in debug mode
    if (ENABLE_DEBUG_LOGS) {
      console.error('[API Response Error]', {
        status: error.response?.status,
        url: error.config?.url,
        message: error.message,
      });
    }

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Try to refresh token
      try {
        const refreshToken = typeof window !== 'undefined' ? localStorage.getItem(refreshTokenKey) : null;
        
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token } = response.data;
          
          if (typeof window !== 'undefined') {
            localStorage.setItem(tokenKey, access_token);
          }

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        if (typeof window !== 'undefined') {
          localStorage.removeItem(tokenKey);
          localStorage.removeItem(refreshTokenKey);
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    // Handle other errors
    return Promise.reject(error);
  }
);

/**
 * API Error Handler
 * Extracts error message from API response
 */
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.message || error.message || 'An unexpected error occurred';
  }
  return 'An unexpected error occurred';
};

export default apiClient;
