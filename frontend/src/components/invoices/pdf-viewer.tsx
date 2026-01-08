'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  ZoomIn,
  ZoomOut,
  RotateCw,
  Download,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
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
  const viewerRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    let viewer: any = null;

    const initViewer = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Check if Foxit SDK is available
        const foxitSDKPath = process.env.NEXT_PUBLIC_FOXIT_SDK_PATH || '/foxit-lib';
        const licenseKey = process.env.NEXT_PUBLIC_FOXIT_LICENSE_KEY;

        if (!licenseKey || licenseKey === 'trial-license-key') {
          throw new Error('Foxit license key not configured. Please set NEXT_PUBLIC_FOXIT_LICENSE_KEY in your .env.local file.');
        }

        // Dynamically import Foxit SDK
        const PDFViewerSDK = await import('@foxitsoftware/foxit-pdf-sdk-for-web-library');

        if (!isMounted) return;

        // Initialize viewer
        viewer = new PDFViewerSDK.default({
          libPath: foxitSDKPath,
          jr: {
            licenseSN: 'foxit-trial',
            licenseKey: licenseKey,
          },
        });

        if (!containerRef.current) return;

        // Open PDF document
        const doc = await viewer.openPDFByHttpRangeRequest(documentUrl, {});
        
        if (!isMounted) return;

        viewerRef.current = viewer;

        // Get document info
        const pageCount = await doc.getPageCount();
        setTotalPages(pageCount);
        setIsLoading(false);

        if (onDocumentLoad) {
          onDocumentLoad();
        }
      } catch (err) {
        console.error('Failed to initialize PDF viewer:', err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to load PDF document';
        setError(errorMessage);
        setIsLoading(false);
        
        if (onDocumentError) {
          onDocumentError(err instanceof Error ? err : new Error(errorMessage));
        }
      }
    };

    initViewer();

    return () => {
      isMounted = false;
      if (viewer) {
        try {
          viewer.destroy();
        } catch (err) {
          console.error('Error cleaning up viewer:', err);
        }
      }
    };
  }, [documentUrl, onDocumentLoad, onDocumentError]);

  const handleZoomIn = () => {
    const newScale = Math.min(scale + 0.25, 3.0);
    setScale(newScale);
    if (viewerRef.current) {
      viewerRef.current.zoomTo(newScale);
    }
  };

  const handleZoomOut = () => {
    const newScale = Math.max(scale - 0.25, 0.5);
    setScale(newScale);
    if (viewerRef.current) {
      viewerRef.current.zoomTo(newScale);
    }
  };

  const handleRotate = () => {
    const newRotation = (rotation + 90) % 360;
    setRotation(newRotation);
    if (viewerRef.current) {
      viewerRef.current.rotatePage(newRotation);
    }
  };

  const handlePreviousPage = () => {
    if (currentPage > 1 && viewerRef.current) {
      const newPage = currentPage - 1;
      setCurrentPage(newPage);
      viewerRef.current.goToPage(newPage - 1); // 0-indexed
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages && viewerRef.current) {
      const newPage = currentPage + 1;
      setCurrentPage(newPage);
      viewerRef.current.goToPage(newPage - 1); // 0-indexed
    }
  };

  const handleDownload = async () => {
    try {
      const response = await fetch(documentUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName || 'invoice.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to download PDF:', err);
    }
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
        <div className="flex flex-col items-center justify-center min-h-[600px] space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="text-sm text-muted-foreground">Loading PDF document...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-8 ${className}`}>
        <div className="flex flex-col items-center justify-center min-h-[600px] space-y-4">
          <div className="rounded-full bg-destructive/10 p-3">
            <svg
              className="h-6 w-6 text-destructive"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
          <div className="text-center">
            <h3 className="font-semibold text-lg mb-2">Failed to Load PDF</h3>
            <p className="text-sm text-muted-foreground max-w-md">{error}</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div ref={containerRef} className={`flex flex-col ${className}`}>
      {/* Toolbar */}
      <Card className="p-2 mb-2">
        <div className="flex items-center justify-between gap-2">
          {/* Page Navigation */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviousPage}
              disabled={currentPage === 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm min-w-[100px] text-center">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleZoomOut} disabled={scale <= 0.5}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm min-w-[60px] text-center">{Math.round(scale * 100)}%</span>
            <Button variant="outline" size="sm" onClick={handleZoomIn} disabled={scale >= 3.0}>
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleRotate}>
              <RotateCw className="h-4 w-4" />
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

      {/* PDF Viewer Container */}
      <Card className="flex-1 min-h-[600px] overflow-hidden">
        <div className="w-full h-full bg-muted/30" id="pdf-viewer-container">
          {/* Foxit PDF viewer will be rendered here */}
        </div>
      </Card>
    </div>
  );
}
