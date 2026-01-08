// Type definitions for Foxit PDF SDK for Web

export interface Annotation {
  id: string;
  type: 'highlight' | 'note' | 'drawing';
  pageIndex: number;
  content?: string;
  color?: string;
  rect?: { x: number; y: number; width: number; height: number };
  author?: string;
  createdDate?: Date;
}

declare module '@foxitsoftware/foxit-pdf-sdk-for-web-library' {
  export interface PDFViewerOptions {
    libPath: string;
    jr: {
      licenseSN: string;
      licenseKey: string;
    };
  }

  export interface PDFDocument {
    close(): Promise<void>;
    getPageCount(): Promise<number>;
    getPage(index: number): Promise<PDFPage>;
    save(): Promise<Blob>;
  }

  export interface PDFPage {
    render(options: RenderOptions): Promise<void>;
    getSize(): Promise<{ width: number; height: number }>;
  }

  export interface RenderOptions {
    canvas: HTMLCanvasElement;
    scale?: number;
    rotation?: number;
  }

  export class PDFViewer {
    constructor(options: PDFViewerOptions);
    openPDFByHttpRangeRequest(url: string, options?: any): Promise<PDFDocument>;
    getCurrentPDFDoc(): PDFDocument | null;
    goToPage(pageIndex: number): Promise<void>;
    zoomTo(scale: number): Promise<void>;
    rotatePage(rotation: number): Promise<void>;
    destroy(): void;
  }

  export default PDFViewer;
}
