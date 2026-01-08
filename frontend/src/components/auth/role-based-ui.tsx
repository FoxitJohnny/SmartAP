'use client';

import React from 'react';
import { useAuthStore } from '@/stores/authStore';
import type { UserRole } from '@/types';

interface RoleBasedUIProps {
  allowedRoles: UserRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * Component to conditionally render UI based on user role
 */
export function RoleBasedUI({ allowedRoles, children, fallback = null }: RoleBasedUIProps) {
  const user = useAuthStore((state) => state.user);

  if (!user || !allowedRoles.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

/**
 * Hook to check if user has a specific role
 */
export function useHasRole(role: UserRole): boolean {
  const user = useAuthStore((state) => state.user);
  return user?.role === role;
}

/**
 * Hook to check if user has any of the specified roles
 */
export function useHasAnyRole(roles: UserRole[]): boolean {
  const user = useAuthStore((state) => state.user);
  return user ? roles.includes(user.role) : false;
}

/**
 * Hook to get current user role
 */
export function useCurrentRole(): UserRole | null {
  const user = useAuthStore((state) => state.user);
  return user?.role || null;
}

/**
 * Check if role can approve invoices
 */
export function canApprove(role: UserRole): boolean {
  return ['MANAGER', 'AUDITOR', 'ADMIN'].includes(role);
}

/**
 * Check if role can reject invoices
 */
export function canReject(role: UserRole): boolean {
  return ['MANAGER', 'AUDITOR', 'ADMIN'].includes(role);
}

/**
 * Check if role can escalate invoices
 */
export function canEscalate(role: UserRole): boolean {
  return ['AP_CLERK', 'MANAGER', 'AUDITOR'].includes(role);
}

/**
 * Check if role can request changes
 */
export function canRequestChanges(role: UserRole): boolean {
  return true; // All roles can request changes
}

/**
 * Check if role can view approval queue
 */
export function canViewApprovalQueue(role: UserRole): boolean {
  return true; // All roles can view the queue
}

/**
 * Check if role can perform bulk operations
 */
export function canBulkApprove(role: UserRole): boolean {
  return ['MANAGER', 'ADMIN'].includes(role);
}

/**
 * Get role display name
 */
export function getRoleDisplayName(role: UserRole): string {
  const roleNames: Record<UserRole, string> = {
    AP_CLERK: 'AP Clerk',
    MANAGER: 'Manager',
    AUDITOR: 'Auditor',
    ADMIN: 'Administrator',
  };
  return roleNames[role] || role;
}

/**
 * Get role description
 */
export function getRoleDescription(role: UserRole): string {
  const descriptions: Record<UserRole, string> = {
    AP_CLERK: 'Can view invoices, add comments, and request changes',
    MANAGER: 'Can approve, reject, and escalate invoices',
    AUDITOR: 'Can review invoices, flag issues, and require additional information',
    ADMIN: 'Full system access including user management and configuration',
  };
  return descriptions[role] || 'No description available';
}
