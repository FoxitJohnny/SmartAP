'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
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
  Link2,
  Link2Off,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface DualPdfViewerProps {
  leftUrl: string;
  leftLabel: string;
  leftFileName?: string;
  rightUrl: string;
  rightLabel: string;
  rightFileName?: string;
  className?: string;
}

type PdfStatus = 'loading' | 'ready' | 'error';

/**
 * Resolves a possibly-relative PDF URL to an absolute one using the backend base.
 */
function resolvePdfUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  return `${apiBase.replace('/api/v1', '')}${url}`;
}

export function DualPdfViewer({
  leftUrl,
  leftLabel,
  leftFileName,
  rightUrl,
  rightLabel,
  rightFileName,
  className = '',
}: DualPdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const leftIframeRef = useRef<HTMLIFrameElement>(null);
  const rightIframeRef = useRef<HTMLIFrameElement>(null);

  // State
  const [leftStatus, setLeftStatus] = useState<PdfStatus>('loading');
  const [rightStatus, setRightStatus] = useState<PdfStatus>('loading');
  const [zoom, setZoom] = useState(100);
  const [appliedZoom, setAppliedZoom] = useState(100);
  const [page, setPage] = useState(1);
  const [synced, setSynced] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const resolvedLeft = resolvePdfUrl(leftUrl);
  const resolvedRight = resolvePdfUrl(rightUrl);

  // --- Debounce zoom so iframe doesn't remount on every click rapidly ----------
  useEffect(() => {
    const t = setTimeout(() => setAppliedZoom(zoom), 350);
    return () => clearTimeout(t);
  }, [zoom]);

  // --- PDF availability check ---------------------------------------------------
  const checkPdf = useCallback(
    async (url: string, setStatus: (s: PdfStatus) => void) => {
      try {
        setStatus('loading');
        let res = await fetch(url, { method: 'HEAD' });
        if (res.status === 405) {
          res = await fetch(url, { method: 'GET', headers: { Range: 'bytes=0-0' } });
        }
        if (!res.ok && res.status !== 206) throw new Error(`${res.status}`);
        setStatus('ready');
      } catch {
        setStatus('error');
      }
    },
    [],
  );

  useEffect(() => {
    checkPdf(resolvedLeft, setLeftStatus);
  }, [resolvedLeft, checkPdf]);

  useEffect(() => {
    checkPdf(resolvedRight, setRightStatus);
  }, [resolvedRight, checkPdf]);

  // --- Build iframe src with PDF Open Parameters --------------------------------
  // Uses the standard PDF URL fragment specification supported by Chrome, Edge,
  // and Firefox — #zoom=<scale>&page=<n>.  The browser's native PDF viewer reads
  // these and renders at the *correct* resolution (no CSS-transform blur).
  const buildSrc = useCallback(
    (baseUrl: string) =>
      `${baseUrl}#page=${page}&zoom=${appliedZoom}&toolbar=0&navpanes=0`,
    [page, appliedZoom],
  );

  // Force iframe remount when zoom or page changes so the PDF viewer re-reads
  // the URL fragment.  Zoom is debounced via appliedZoom to avoid rapid reloads.
  const iframeKey = `z${appliedZoom}-p${page}`;

  // --- Zoom controls -----------------------------------------------------------
  const zoomIn = () => setZoom((z) => Math.min(z + 25, 250));
  const zoomOut = () => setZoom((z) => Math.max(z - 25, 50));
  const zoomReset = () => setZoom(100);

  // --- Page navigation (synced) -------------------------------------------------
  const prevPage = () => setPage((p) => Math.max(1, p - 1));
  const nextPage = () => setPage((p) => p + 1);

  // --- Download ----------------------------------------------------------------
  const downloadPdf = async (url: string, name: string) => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(blobUrl);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  // --- Fullscreen --------------------------------------------------------------
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!isFullscreen) {
      containerRef.current.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  // --- Render helpers ----------------------------------------------------------
  const renderPane = (
    url: string,
    label: string,
    fileName: string | undefined,
    status: PdfStatus,
    iframeRef: React.RefObject<HTMLIFrameElement | null>,
    accentColor: string,
  ) => {
    const headerBg =
      accentColor === 'blue'
        ? 'bg-blue-50 dark:bg-blue-950/30'
        : 'bg-green-50 dark:bg-green-950/30';
    const headerText =
      accentColor === 'blue'
        ? 'text-blue-700 dark:text-blue-300'
        : 'text-green-700 dark:text-green-300';

    return (
      <div className="flex flex-col flex-1 min-w-0">
        {/* Pane header */}
        <div
          className={`flex items-center justify-between px-3 py-2 rounded-t-lg border border-b-0 ${headerBg}`}
        >
          <span className={`text-sm font-semibold ${headerText} truncate`}>
            {label}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => window.open(url, '_blank')}
              title="Open in new tab"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => downloadPdf(url, fileName || `${label}.pdf`)}
              title="Download"
            >
              <Download className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        {/* PDF content area */}
        <div className="flex-1 border rounded-b-lg overflow-hidden bg-white">
          {status === 'loading' && (
            <div className="flex flex-col items-center justify-center h-full space-y-3 bg-muted/20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary" />
              <p className="text-sm text-muted-foreground">Loading PDF…</p>
            </div>
          )}
          {status === 'error' && (
            <div className="flex flex-col items-center justify-center h-full space-y-3 bg-muted/20">
              <FileText className="h-10 w-10 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                PDF preview unavailable
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(url, '_blank')}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Open in New Tab
              </Button>
            </div>
          )}
          {status === 'ready' && (
            <iframe
              key={iframeKey}
              ref={iframeRef}
              src={buildSrc(url)}
              className="w-full h-full border-0"
              title={label}
            />
          )}
        </div>
      </div>
    );
  };

  // --- Main render -------------------------------------------------------------
  return (
    <div ref={containerRef} className={`flex flex-col ${className}`}>
      {/* Shared toolbar */}
      <Card className="p-2 mb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          {/* Zoom controls */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={zoomOut}
              disabled={zoom <= 50}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm min-w-[50px] text-center font-mono">
              {zoom}%
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={zoomIn}
              disabled={zoom >= 250}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={zoomReset}
              title="Reset zoom"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>

          {/* Page navigation + sync toggle */}
          <div className="flex items-center gap-2">
            {synced && (
              <div className="flex items-center gap-1.5 border-r pr-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={prevPage}
                  disabled={page <= 1}
                  className="h-8 w-8 p-0"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm min-w-[60px] text-center">
                  Page {page}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={nextPage}
                  className="h-8 w-8 p-0"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
            <Button
              variant={synced ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSynced((v) => !v)}
              title={
                synced
                  ? 'Page sync ON — both PDFs navigate together'
                  : 'Page sync OFF — scroll each PDF independently'
              }
              className="gap-1.5"
            >
              {synced ? (
                <>
                  <Link2 className="h-4 w-4" />
                  <span className="text-xs">Page Synced</span>
                </>
              ) : (
                <>
                  <Link2Off className="h-4 w-4" />
                  <span className="text-xs">Independent</span>
                </>
              )}
            </Button>
          </div>

          {/* Fullscreen */}
          <Button variant="outline" size="sm" onClick={toggleFullscreen}>
            {isFullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
        </div>
      </Card>

      {/* Two-pane PDF area */}
      <div
        className="grid grid-cols-2 gap-3"
        style={{ height: isFullscreen ? 'calc(100vh - 56px)' : '800px' }}
      >
        {renderPane(
          resolvedLeft,
          leftLabel,
          leftFileName,
          leftStatus,
          leftIframeRef,
          'blue',
        )}
        {renderPane(
          resolvedRight,
          rightLabel,
          rightFileName,
          rightStatus,
          rightIframeRef,
          'green',
        )}
      </div>
    </div>
  );
}
