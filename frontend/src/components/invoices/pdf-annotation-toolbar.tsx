'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Highlighter,
  MessageSquare,
  Edit3,
  Eraser,
  Save,
  X,
} from 'lucide-react';
import type { Annotation } from '@/types/foxit';

interface PDFAnnotationToolbarProps {
  onAnnotationCreate: (annotation: Partial<Annotation>) => void;
  onAnnotationDelete: (annotationId: string) => void;
  annotations: Annotation[];
  currentPage: number;
}

type AnnotationMode = 'none' | 'highlight' | 'note' | 'drawing';

export function PDFAnnotationToolbar({
  onAnnotationCreate,
  onAnnotationDelete,
  annotations,
  currentPage,
}: PDFAnnotationToolbarProps) {
  const [mode, setMode] = useState<AnnotationMode>('none');
  const [noteContent, setNoteContent] = useState('');
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [selectedColor, setSelectedColor] = useState('#FFFF00'); // Yellow

  const pageAnnotations = annotations.filter((a) => a.pageIndex === currentPage - 1);

  const handleModeChange = (newMode: AnnotationMode) => {
    setMode(newMode);
    if (newMode === 'note') {
      setShowNoteInput(true);
    } else {
      setShowNoteInput(false);
    }
  };

  const handleCreateNote = () => {
    if (!noteContent.trim()) return;

    onAnnotationCreate({
      type: 'note',
      pageIndex: currentPage - 1,
      content: noteContent,
      color: selectedColor,
      author: 'Current User', // TODO: Get from auth context
      createdDate: new Date(),
    });

    setNoteContent('');
    setShowNoteInput(false);
    setMode('none');
  };

  const handleCreateHighlight = () => {
    // This would typically be triggered by selecting text in the PDF
    onAnnotationCreate({
      type: 'highlight',
      pageIndex: currentPage - 1,
      color: selectedColor,
      author: 'Current User',
      createdDate: new Date(),
    });
    setMode('none');
  };

  const colors = [
    { name: 'Yellow', value: '#FFFF00' },
    { name: 'Green', value: '#00FF00' },
    { name: 'Blue', value: '#00BFFF' },
    { name: 'Red', value: '#FF6B6B' },
    { name: 'Orange', value: '#FFA500' },
    { name: 'Purple', value: '#9B59B6' },
  ];

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <h3 className="font-semibold mb-3">Annotation Tools</h3>
        
        {/* Tool Buttons */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          <Button
            variant={mode === 'highlight' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleModeChange('highlight')}
            className="justify-start"
          >
            <Highlighter className="h-4 w-4 mr-2" />
            Highlight
          </Button>
          <Button
            variant={mode === 'note' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleModeChange('note')}
            className="justify-start"
          >
            <MessageSquare className="h-4 w-4 mr-2" />
            Note
          </Button>
          <Button
            variant={mode === 'drawing' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleModeChange('drawing')}
            className="justify-start"
          >
            <Edit3 className="h-4 w-4 mr-2" />
            Draw
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setMode('none')}
            className="justify-start"
          >
            <Eraser className="h-4 w-4 mr-2" />
            Clear Mode
          </Button>
        </div>

        {/* Color Picker */}
        <div className="mb-4">
          <Label className="text-sm mb-2">Color</Label>
          <div className="flex gap-2 flex-wrap">
            {colors.map((color) => (
              <button
                key={color.value}
                className={`w-8 h-8 rounded-full border-2 transition-all ${
                  selectedColor === color.value
                    ? 'border-primary scale-110'
                    : 'border-muted-foreground/20'
                }`}
                style={{ backgroundColor: color.value }}
                onClick={() => setSelectedColor(color.value)}
                title={color.name}
              />
            ))}
          </div>
        </div>

        {/* Note Input */}
        {showNoteInput && (
          <div className="space-y-2">
            <Label htmlFor="note-content">Note Content</Label>
            <Input
              id="note-content"
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Enter your note..."
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleCreateNote();
                }
              }}
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleCreateNote}>
                <Save className="h-4 w-4 mr-2" />
                Save Note
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setShowNoteInput(false);
                  setNoteContent('');
                  setMode('none');
                }}
              >
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Annotations List */}
      {pageAnnotations.length > 0 && (
        <Card className="p-4">
          <h3 className="font-semibold mb-3">Page Annotations ({pageAnnotations.length})</h3>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {pageAnnotations.map((annotation) => (
              <div
                key={annotation.id}
                className="p-2 border rounded-lg bg-muted/30 text-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {annotation.type === 'highlight' && (
                        <Highlighter className="h-3 w-3" />
                      )}
                      {annotation.type === 'note' && (
                        <MessageSquare className="h-3 w-3" />
                      )}
                      {annotation.type === 'drawing' && <Edit3 className="h-3 w-3" />}
                      <span className="font-medium capitalize">{annotation.type}</span>
                      {annotation.color && (
                        <div
                          className="w-3 h-3 rounded-full border"
                          style={{ backgroundColor: annotation.color }}
                        />
                      )}
                    </div>
                    {annotation.content && (
                      <p className="text-muted-foreground">{annotation.content}</p>
                    )}
                    {annotation.author && (
                      <p className="text-xs text-muted-foreground mt-1">
                        by {annotation.author}
                        {annotation.createdDate &&
                          ` • ${new Date(annotation.createdDate).toLocaleDateString()}`}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onAnnotationDelete(annotation.id)}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
