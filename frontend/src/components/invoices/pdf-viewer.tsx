'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  ZoomIn,
  ZoomOut,
  Download,
  Maximize2,
  Minimize2,
  FileText,
  ExternalLink,
} from 'lucide-react';

interface PDFViewerProps {
  documentUrl: string;
  fileName?: string;
  onDocumentLoad?: () => void;
  onDocumentError?: (error: Error) => void;
  className?: string;
}

export function PDFViewer({
  documentUrl,
  fileName,
  onDocumentLoad,
  onDocumentError,
  className = '',
}: PDFViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Construct the actual PDF URL from the backend
  const getPdfUrl = () => {
    // If it's already an absolute URL, use it
    if (documentUrl.startsWith('http://') || documentUrl.startsWith('https://')) {
      return documentUrl;
    }
    // Otherwise, construct from backend API
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const backendBaseUrl = apiBaseUrl.replace('/api/v1', '');
    return `${backendBaseUrl}${documentUrl}`;
  };

  useEffect(() => {
    const url = getPdfUrl();
    
    // Check if PDF URL is valid
    const checkPdf = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Try HEAD first, fall back to GET if not supported
        let response = await fetch(url, { method: 'HEAD' });
        
        // If HEAD returns 405 (Method Not Allowed), try GET
        if (response.status === 405) {
          response = await fetch(url, { method: 'GET', headers: { 'Range': 'bytes=0-0' } });
        }
        
        if (!response.ok && response.status !== 206) {
          throw new Error(`PDF not found (${response.status})`);
        }
        
        setIsLoading(false);
        if (onDocumentLoad) {
          onDocumentLoad();
        }
      } catch (err) {
        console.error('Failed to load PDF:', err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to load PDF document';
        setError(errorMessage);
        setIsLoading(false);
        
        if (onDocumentError) {
          onDocumentError(err instanceof Error ? err : new Error(errorMessage));
        }
      }
    };

    if (documentUrl) {
      checkPdf();
    } else {
      setError('No PDF URL provided');
      setIsLoading(false);
    }
  }, [documentUrl, onDocumentLoad, onDocumentError]);

  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 25, 200));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 25, 50));
  };

  const handleDownload = async () => {
    try {
      const url = getPdfUrl();
      const response = await fetch(url);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = fileName || 'invoice.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to download PDF:', err);
    }
  };

  const handleOpenInNewTab = () => {
    window.open(getPdfUrl(), '_blank');
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;

    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  if (isLoading) {
    return (
      <Card className={`p-8 ${className}`}>
        <div className="flex flex-col items-center justify-center h-[400px] space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="text-sm text-muted-foreground">Loading PDF document...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-8 ${className}`}>
        <div className="flex flex-col items-center justify-center h-[400px] space-y-4">
          <div className="rounded-full bg-muted p-4">
            <FileText className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center">
            <h3 className="font-semibold text-lg mb-2">PDF Preview Unavailable</h3>
            <p className="text-sm text-muted-foreground max-w-md mb-4">{error}</p>
            {documentUrl && (
              <Button variant="outline" onClick={handleOpenInNewTab}>
                <ExternalLink className="h-4 w-4 mr-2" />
                Open PDF in New Tab
              </Button>
            )}
          </div>
        </div>
      </Card>
    );
  }

  const pdfUrl = getPdfUrl();

  return (
    <div ref={containerRef} className={`flex flex-col ${className}`}>
      {/* Toolbar */}
      <Card className="p-2 mb-2">
        <div className="flex items-center justify-between gap-2">
          {/* Zoom Controls */}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleZoomOut} disabled={scale <= 50}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm min-w-[60px] text-center">{scale}%</span>
            <Button variant="outline" size="sm" onClick={handleZoomIn} disabled={scale >= 200}>
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleOpenInNewTab}>
              <ExternalLink className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={toggleFullscreen}>
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </Card>

      {/* PDF Viewer Container - Using iframe with browser's built-in PDF viewer */}
      <Card className="overflow-hidden" style={{ height: '1000px' }}>
        <div 
          className="w-full h-full bg-muted/30" 
          style={{ 
            transform: `scale(${scale / 100})`,
            transformOrigin: 'top left',
            width: `${10000 / scale}%`,
            height: `${10000 / scale}%`,
          }}
        >
          <iframe
            ref={iframeRef}
            src={`${pdfUrl}#toolbar=1&navpanes=0&scrollbar=1`}
            className="w-full h-full border-0"
            title={fileName || 'PDF Document'}
          />
        </div>
      </Card>
    </div>
  );
}
