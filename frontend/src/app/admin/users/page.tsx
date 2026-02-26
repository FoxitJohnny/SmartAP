'use client';

import { useState } from 'react';
import { useUsers, useUpdateUser, type UserListItem, type UserUpdateRequest } from '@/lib/api/users';
import { useAuthStore } from '@/stores/authStore';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
import { toast } from 'sonner';

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Admin' },
  { value: 'finance_manager', label: 'Finance Manager' },
  { value: 'accountant', label: 'Accountant' },
  { value: 'viewer', label: 'Viewer' },
];

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  finance_manager: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  accountant: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  viewer: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
};

function formatRole(role: string): string {
  return role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(iso?: string): string {
  if (!iso) return 'Never';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function UsersPage() {
  const { user: currentUser } = useAuthStore();
  const { data: users, isLoading, error } = useUsers();
  const updateMutation = useUpdateUser();
  const [editingUser, setEditingUser] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<UserUpdateRequest>({});

  // Check admin access
  if (currentUser?.role !== 'admin' && currentUser?.role !== 'ADMIN') {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <Card className="w-full max-w-md">
            <CardContent className="pt-6 text-center">
              <svg className="mx-auto h-12 w-12 text-muted-foreground mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <h2 className="text-lg font-semibold mb-1">Access Denied</h2>
              <p className="text-sm text-muted-foreground">Only administrators can manage users.</p>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  const handleEdit = (user: UserListItem) => {
    setEditingUser(user.id);
    setEditValues({ role: user.role, is_active: user.is_active });
  };

  const handleSave = async (userId: string) => {
    try {
      await updateMutation.mutateAsync({ userId, data: editValues });
      toast.success('User updated');
      setEditingUser(null);
      setEditValues({});
    } catch {
      toast.error('Failed to update user');
    }
  };

  const handleCancel = () => {
    setEditingUser(null);
    setEditValues({});
  };

  const handleToggleActive = async (user: UserListItem) => {
    try {
      await updateMutation.mutateAsync({
        userId: user.id,
        data: { is_active: !user.is_active },
      });
      toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`);
    } catch {
      toast.error('Failed to update user status');
    }
  };

  return (
    <DashboardLayout>
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
        <p className="text-muted-foreground">Manage user accounts, roles, and access.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
          <CardDescription>
            {users ? `${users.length} registered user${users.length === 1 ? '' : 's'}` : 'Loading...'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          )}

          {error && (
            <div className="text-center py-8 text-destructive">
              Failed to load users. Make sure you have admin access.
            </div>
          )}

          {users && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => {
                  const isEditing = editingUser === user.id;
                  const isSelf = user.id === currentUser?.id;
                  return (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.full_name}</TableCell>
                      <TableCell className="text-muted-foreground">{user.email}</TableCell>
                      <TableCell>
                        {isEditing ? (
                          <Select
                            value={editValues.role || user.role}
                            onValueChange={(v) => setEditValues({ ...editValues, role: v })}
                          >
                            <SelectTrigger className="w-[160px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {ROLE_OPTIONS.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                  {opt.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge variant="secondary" className={ROLE_COLORS[user.role] || ''}>
                            {formatRole(user.role)}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>{user.department || '—'}</TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? 'default' : 'destructive'}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatDate(user.last_login)}
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                        {isEditing ? (
                          <>
                            <Button size="sm" onClick={() => handleSave(user.id)} disabled={updateMutation.isPending}>
                              Save
                            </Button>
                            <Button size="sm" variant="ghost" onClick={handleCancel}>
                              Cancel
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button size="sm" variant="outline" onClick={() => handleEdit(user)}>
                              Edit Role
                            </Button>
                            {!isSelf && (
                              <Button
                                size="sm"
                                variant={user.is_active ? 'destructive' : 'default'}
                                onClick={() => handleToggleActive(user)}
                                disabled={updateMutation.isPending}
                              >
                                {user.is_active ? 'Deactivate' : 'Activate'}
                              </Button>
                            )}
                          </>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
    </DashboardLayout>
  );
}
