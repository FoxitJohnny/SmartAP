"use client"

import * as React from "react"
import { toast as sonnerToast } from "sonner"

type ToastProps = {
  title?: string
  description?: string
  variant?: "default" | "destructive"
}

function useToast() {
  const toast = React.useCallback(
    ({ title, description, variant = "default" }: ToastProps) => {
      if (variant === "destructive") {
        sonnerToast.error(title, {
          description,
        })
      } else {
        sonnerToast(title, {
          description,
        })
      }
    },
    []
  )

  return { toast }
}

export { useToast }
export type { ToastProps }
