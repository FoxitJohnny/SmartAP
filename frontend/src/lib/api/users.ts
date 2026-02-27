/**
 * Users API Client
 * 
 * Admin-only user management endpoints.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface UserListItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  department?: string;
  is_active: boolean;
  created_at?: string;
  last_login?: string;
}

export interface UserUpdateRequest {
  role?: string;
  department?: string;
  is_active?: boolean;
}

export const usersApi = {
  list: async (): Promise<UserListItem[]> => {
    const response = await apiClient.get<UserListItem[]>('/auth/users');
    return response.data;
  },
  update: async (userId: string, data: UserUpdateRequest): Promise<UserListItem> => {
    const response = await apiClient.put<UserListItem>(`/auth/users/${userId}`, data);
    return response.data;
  },
};

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    staleTime: 30_000,
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserUpdateRequest }) =>
      usersApi.update(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
