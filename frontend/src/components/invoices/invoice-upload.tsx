'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useUploadInvoice } from '@/lib/api/invoices';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface UploadedFile {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  invoiceId?: string;
}

interface InvoiceUploadProps {
  onUploadComplete?: (invoiceId: string) => void;
}

export function InvoiceUpload({ onUploadComplete }: InvoiceUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const uploadMutation = useUploadInvoice();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      // Add files to state
      const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
        file,
        progress: 0,
        status: 'pending' as const,
      }));
      setFiles((prev) => [...prev, ...newFiles]);

      // Upload each file
      for (let i = 0; i < acceptedFiles.length; i++) {
        const file = acceptedFiles[i];
        const fileIndex = files.length + i;

        try {
          // Update status to uploading
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === fileIndex ? { ...f, status: 'uploading' as const } : f
            )
          );

          const result = await uploadMutation.mutateAsync({
            file,
            onProgress: (progress) => {
              setFiles((prev) =>
                prev.map((f, idx) =>
                  idx === fileIndex ? { ...f, progress } : f
                )
              );
            },
          });

          // Update status to success
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === fileIndex
                ? {
                    ...f,
                    status: 'success' as const,
                    progress: 100,
                    invoiceId: result.invoice_id,
                  }
                : f
            )
          );

          toast.success(`${file.name} uploaded successfully`);
          if (onUploadComplete && result.invoice_id) {
            onUploadComplete(result.invoice_id);
          }
        } catch (error: any) {
          // Update status to error
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === fileIndex
                ? {
                    ...f,
                    status: 'error' as const,
                    error: error?.response?.data?.message || 'Upload failed',
                  }
                : f
            )
          );
          toast.error(`Failed to upload ${file.name}`);
        }
      }
    },
    [files.length, uploadMutation, onUploadComplete]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/tiff': ['.tif', '.tiff'],
    },
    multiple: true,
  });

  const clearCompleted = () => {
    setFiles((prev) => prev.filter((f) => f.status === 'uploading'));
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Upload Invoices</CardTitle>
          <CardDescription>
            Drag and drop invoice files or click to browse. Supports PDF, PNG, JPG, and TIFF.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={cn(
              'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
              isDragActive
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-primary/50'
            )}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-2">
              <svg
                className="w-12 h-12 text-muted-foreground"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              {isDragActive ? (
                <p className="text-lg font-medium">Drop files here...</p>
              ) : (
                <>
                  <p className="text-lg font-medium">
                    Drag & drop invoice files here
                  </p>
                  <p className="text-sm text-muted-foreground">
                    or click to select files
                  </p>
                </>
              )}
              <p className="text-xs text-muted-foreground mt-2">
                Maximum file size: 10MB per file
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {files.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Upload Progress</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearCompleted}
                disabled={!files.some((f) => f.status === 'success' || f.status === 'error')}
              >
                Clear Completed
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {files.map((file, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <div className="flex-shrink-0">
                        {file.status === 'success' && (
                          <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                        {file.status === 'error' && (
                          <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        )}
                        {(file.status === 'pending' || file.status === 'uploading') && (
                          <svg className="w-5 h-5 text-blue-500 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{file.file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(file.file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground ml-4">
                      {file.status === 'uploading' && `${file.progress}%`}
                      {file.status === 'success' && 'Complete'}
                      {file.status === 'error' && 'Failed'}
                    </div>
                  </div>
                  {file.status === 'uploading' && (
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                  {file.status === 'error' && file.error && (
                    <p className="text-xs text-red-500">{file.error}</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
