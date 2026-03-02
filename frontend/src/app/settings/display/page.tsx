'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, RotateCcw, Check } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { useDealPageWidgets, useSaveDealPageWidgets, DEFAULT_DEAL_WIDGETS, type WidgetConfig } from '@/lib/hooks/use-preferences';

function SortableWidget({
  widget,
  onToggle,
}: {
  widget: WidgetConfig;
  onToggle: (id: string, visible: boolean) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3"
    >
      <button
        className="cursor-grab touch-none text-muted-foreground hover:text-foreground"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-4" />
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{widget.label}</p>
        <p className="text-xs text-muted-foreground">{widget.description}</p>
      </div>
      <Switch
        checked={widget.visible}
        onCheckedChange={(checked) => onToggle(widget.id, checked)}
      />
    </div>
  );
}

export default function DisplaySettingsPage() {
  const { data: serverWidgets, isLoading } = useDealPageWidgets();
  const saveMutation = useSaveDealPageWidgets();
  const [widgets, setWidgets] = useState<WidgetConfig[]>([]);
  const [saved, setSaved] = useState(false);

  // Sync server data to local state (use defaults as fallback)
  useEffect(() => {
    if (widgets.length === 0) {
      const source = serverWidgets && serverWidgets.length > 0 ? serverWidgets : DEFAULT_DEAL_WIDGETS;
      setWidgets([...source].sort((a, b) => a.order - b.order));
    }
  }, [serverWidgets, widgets.length]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const save = useCallback(
    (updated: WidgetConfig[]) => {
      const reordered = updated.map((w, i) => ({ ...w, order: i }));
      setWidgets(reordered);
      saveMutation.mutate(reordered, {
        onSuccess: () => {
          setSaved(true);
          setTimeout(() => setSaved(false), 2000);
        },
      });
    },
    [saveMutation],
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = widgets.findIndex((w) => w.id === active.id);
    const newIndex = widgets.findIndex((w) => w.id === over.id);
    const moved = arrayMove(widgets, oldIndex, newIndex);
    save(moved);
  };

  const handleToggle = (id: string, visible: boolean) => {
    const updated = widgets.map((w) =>
      w.id === id ? { ...w, visible } : w,
    );
    save(updated);
  };

  const handleReset = () => {
    const defaults = DEFAULT_DEAL_WIDGETS.map((w, i) => ({
      ...w,
      visible: true,
      order: i,
    }));
    save(defaults);
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 w-48 rounded bg-muted" />
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-16 rounded-lg border bg-muted/20" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Display Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Customize which widgets appear on deal pages and their order.
          Drag to reorder, toggle to show or hide.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-base">Deal Page Widgets</CardTitle>
          <div className="flex items-center gap-2">
            {saved && (
              <span className="text-xs text-emerald-600 flex items-center gap-1">
                <Check className="size-3" /> Saved
              </span>
            )}
            <Button variant="outline" size="sm" onClick={handleReset}>
              <RotateCcw className="size-3.5 mr-1" />
              Reset
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={widgets.map((w) => w.id)}
              strategy={verticalListSortingStrategy}
            >
              {widgets.map((widget) => (
                <SortableWidget
                  key={widget.id}
                  widget={widget}
                  onToggle={handleToggle}
                />
              ))}
            </SortableContext>
          </DndContext>
        </CardContent>
      </Card>
    </div>
  );
}
