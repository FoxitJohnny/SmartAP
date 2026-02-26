import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiClient } from './client';
import { useAuthStore } from '@/stores/authStore';
import type { LoginRequest, LoginResponse, User } from '@/types';

// API functions
export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login/json', credentials);
    return response.data;
  },

  register: async (data: { email: string; password: string; name: string }): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/register', {
      email: data.email,
      password: data.password,
      full_name: data.name,  // Backend expects full_name
    });
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  refreshToken: async (refreshToken: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },
};

// React Query hooks
export function useLogin() {
  const router = useRouter();
  const { login } = useAuthStore();

  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      // Map backend user (full_name) to frontend User (name)
      const user = {
        id: data.user.id,
        email: data.user.email,
        name: data.user.full_name,
        role: data.user.role as any,
        department: data.user.department,
      };
      login(user, data.access_token);
      // Store refresh token
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      router.push('/dashboard');
    },
  });
}

export function useRegister() {
  const router = useRouter();
  const { login } = useAuthStore();

  return useMutation({
    mutationFn: authApi.register,
    onSuccess: (data) => {
      // After registration, redirect to login
      router.push('/login');
    },
  });
}

export function useLogout() {
  const { logout } = useAuthStore();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      logout();
      // Use hard navigation to fully reset all in-memory state
      window.location.href = '/login';
    },
    onError: () => {
      // Even if logout API fails, clear local state
      logout();
      window.location.href = '/login';
    },
  });
}

export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['currentUser'],
    queryFn: authApi.getCurrentUser,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
