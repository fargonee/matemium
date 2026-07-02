import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = "matemium-panel-layout";

export const BOTTOM_COLLAPSE_THRESHOLD = 48;
export const RESIZE_HANDLE_SIZE = 8;
export const MIN_MAIN_COLUMN_WIDTH = 240;
export const MIN_EDITOR_STAGE_HEIGHT = 0;
export const EDITOR_COLLAPSE_THRESHOLD = 20;  // when dragging up, auto-collapse editor below this

export interface PanelLayout {
  sidebarWidth: number;
  chatWidth: number;
  bottomHeight: number;
  bottomPanelOpen: boolean;
  editorOpen: boolean;
}

const DEFAULT_LAYOUT: PanelLayout = {
  sidebarWidth: 260,
  chatWidth: 320,
  bottomHeight: 200,
  bottomPanelOpen: true,
  editorOpen: true,
};

type NumericLayoutKey = Exclude<keyof PanelLayout, "bottomPanelOpen" | "editorOpen">;

const LIMITS: Record<NumericLayoutKey, { min: number; max: number }> = {
  sidebarWidth: { min: 180, max: 480 },
  chatWidth: { min: 240, max: 560 },
  bottomHeight: { min: BOTTOM_COLLAPSE_THRESHOLD, max: 2000 },
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function loadLayout(): PanelLayout {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_LAYOUT;
    const parsed = JSON.parse(raw) as Partial<PanelLayout> & { logPanelOpen?: boolean };
    return {
      sidebarWidth: clamp(
        parsed.sidebarWidth ?? DEFAULT_LAYOUT.sidebarWidth,
        LIMITS.sidebarWidth.min,
        LIMITS.sidebarWidth.max,
      ),
      chatWidth: clamp(
        parsed.chatWidth ?? DEFAULT_LAYOUT.chatWidth,
        LIMITS.chatWidth.min,
        LIMITS.chatWidth.max,
      ),
      bottomHeight: clamp(
        parsed.bottomHeight ?? DEFAULT_LAYOUT.bottomHeight,
        LIMITS.bottomHeight.min,
        LIMITS.bottomHeight.max,
      ),
      bottomPanelOpen:
        parsed.bottomPanelOpen ?? parsed.logPanelOpen ?? DEFAULT_LAYOUT.bottomPanelOpen,
      editorOpen: parsed.editorOpen ?? DEFAULT_LAYOUT.editorOpen,
    };
  } catch {
    return DEFAULT_LAYOUT;
  }
}

function handleGutterWidth(): number {
  return RESIZE_HANDLE_SIZE * 2;
}

function chatWidthLimits(
  containerWidth: number,
  sidebarWidth: number,
): { min: number; max: number } {
  const staticMin = LIMITS.chatWidth.min;
  const staticMax = LIMITS.chatWidth.max;
  if (containerWidth <= 0) {
    return { min: staticMin, max: staticMax };
  }
  const dynamicMax =
    containerWidth -
    sidebarWidth -
    handleGutterWidth() -
    MIN_MAIN_COLUMN_WIDTH;
  return {
    min: staticMin,
    max: Math.max(staticMin, Math.min(staticMax, dynamicMax)),
  };
}

function sidebarWidthLimits(
  containerWidth: number,
  chatWidth: number,
): { min: number; max: number } {
  const staticMin = LIMITS.sidebarWidth.min;
  const staticMax = LIMITS.sidebarWidth.max;
  if (containerWidth <= 0) {
    return { min: staticMin, max: staticMax };
  }
  const dynamicMax =
    containerWidth -
    chatWidth -
    handleGutterWidth() -
    MIN_MAIN_COLUMN_WIDTH;
  return {
    min: staticMin,
    max: Math.max(staticMin, Math.min(staticMax, dynamicMax)),
  };
}

function bottomHeightLimits(regionHeight: number): { min: number; max: number } {
  if (regionHeight <= 0) {
    return { min: BOTTOM_COLLAPSE_THRESHOLD, max: 2000 };
  }
  // Allow the bottom panel to take the full height (editor can be collapsed to 0).
  // The caller decides whether to enforce editor space.
  const BOTTOM_HANDLE_HEIGHT = 10;
  const max = Math.max(BOTTOM_COLLAPSE_THRESHOLD, regionHeight - BOTTOM_HANDLE_HEIGHT);
  return { min: BOTTOM_COLLAPSE_THRESHOLD, max };
}

function fitLayoutToContainer(layout: PanelLayout, containerWidth: number): PanelLayout {
  if (containerWidth <= 0) return layout;

  let next = { ...layout };
  const chatLimits = chatWidthLimits(containerWidth, next.sidebarWidth);
  next.chatWidth = clamp(next.chatWidth, chatLimits.min, chatLimits.max);

  const sidebarLimits = sidebarWidthLimits(containerWidth, next.chatWidth);
  next.sidebarWidth = clamp(next.sidebarWidth, sidebarLimits.min, sidebarLimits.max);

  const chatLimitsAfter = chatWidthLimits(containerWidth, next.sidebarWidth);
  next.chatWidth = clamp(next.chatWidth, chatLimitsAfter.min, chatLimitsAfter.max);

  return next;
}

export function usePanelLayout() {
  const [layout, setLayout] = useState<PanelLayout>(loadLayout);
  const containerWidthRef = useRef(0);
  const editorRegionHeightRef = useRef(0);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  }, [layout]);

  const setContainerWidth = useCallback((width: number) => {
    containerWidthRef.current = width;
    setLayout((prev) => fitLayoutToContainer(prev, width));
  }, []);

  const setEditorRegionHeight = useCallback((height: number) => {
    editorRegionHeightRef.current = height;
    setLayout((prev) => {
      const { min, max } = bottomHeightLimits(height);
      const clamped = clamp(prev.bottomHeight, min, max);
      if (clamped !== prev.bottomHeight) {
        // If clamped to (near) max, treat as editor collapsed
        const atFullMax = clamped >= max - EDITOR_COLLAPSE_THRESHOLD;
        return {
          ...prev,
          bottomHeight: clamped,
          editorOpen: atFullMax ? false : prev.editorOpen,
        };
      }
      return prev;
    });
  }, []);

  const setChatWidthFromPointer = useCallback((clientX: number, containerRight: number) => {
    // Pointer is on the gutter column; chat column is everything to its right.
    const width = containerRight - clientX - RESIZE_HANDLE_SIZE;
    setLayout((prev) => {
      const { min, max } = chatWidthLimits(containerWidthRef.current, prev.sidebarWidth);
      return { ...prev, chatWidth: clamp(width, min, max) };
    });
  }, []);

  const setSidebarWidthFromPointer = useCallback((clientX: number, containerLeft: number) => {
    const width = clientX - containerLeft;
    setLayout((prev) => {
      const { min, max } = sidebarWidthLimits(containerWidthRef.current, prev.chatWidth);
      return { ...prev, sidebarWidth: clamp(width, min, max) };
    });
  }, []);

  const resizeBottom = useCallback((delta: number) => {
    setLayout((prev) => {
      const regionH = editorRegionHeightRef.current;
      if (regionH <= 0) {
        return prev;
      }
      const { max } = bottomHeightLimits(regionH);
      const nextHeight = prev.bottomHeight - delta;

      const impliedEditorSpace = regionH - 10 - nextHeight;

      // Allow dragging all the way up to collapse the editor (bottom takes full height)
      // Also auto-collapse when editor sliver would be too small
      if (nextHeight >= max || (prev.editorOpen && impliedEditorSpace < EDITOR_COLLAPSE_THRESHOLD)) {
        return {
          ...prev,
          bottomPanelOpen: true,
          editorOpen: false,
          bottomHeight: max,
        };
      }

      if (nextHeight < BOTTOM_COLLAPSE_THRESHOLD) {
        return {
          ...prev,
          bottomPanelOpen: false,
          bottomHeight: DEFAULT_LAYOUT.bottomHeight,
          editorOpen: true,
        };
      }

      return {
        ...prev,
        bottomPanelOpen: true,
        editorOpen: true,
        bottomHeight: clamp(nextHeight, BOTTOM_COLLAPSE_THRESHOLD, max),
      };
    });
  }, []);

  const setBottomPanelOpen = useCallback((open: boolean) => {
    setLayout((prev) => {
      if (!open) return { ...prev, bottomPanelOpen: false, editorOpen: true };
      const { min, max } = bottomHeightLimits(editorRegionHeightRef.current);
      // When opening (especially on Render to show progress), force a
      // reasonable fixed height so the main editor + viewport don't get
      // squashed to empty/zero. Use previous only if it was already a good size.
      const wasClosed = !prev.bottomPanelOpen;
      let h = prev.bottomHeight;
      if (wasClosed || h < 220) {
        h = 300; // sensible size for progress panel + logs
      }
      // Never let the dock eat the entire (or most of) the viewport
      const safeMax = Math.max(min, Math.min(max, editorRegionHeightRef.current - 200 || max));
      const reasonableMax = Math.min(safeMax, 420);
      h = clamp(h, min, reasonableMax);
      return { ...prev, bottomPanelOpen: true, editorOpen: true, bottomHeight: h };
    });
  }, []);

  const maximizeBottom = useCallback(() => {
    setLayout((prev) => {
      const { max } = bottomHeightLimits(editorRegionHeightRef.current);
      return {
        ...prev,
        bottomPanelOpen: true,
        editorOpen: false,
        bottomHeight: max,
      };
    });
  }, []);

  const setEditorOpen = useCallback((open: boolean) => {
    setLayout((prev) => {
      const regionH = editorRegionHeightRef.current || 600;
      const handleH = 10;
      if (!open) {
        // Collapse editor fully, bottom takes everything above the handle
        return {
          ...prev,
          editorOpen: false,
          bottomPanelOpen: true,
          bottomHeight: Math.max(regionH - handleH, BOTTOM_COLLAPSE_THRESHOLD),
        };
      }
      // Restore editor with reasonable size (shrink bottom if it was fully expanded)
      let h = prev.bottomHeight;
      const minEditorSpace = 200; // sensible editor space when restoring from full bottom
      if (h > regionH - handleH - minEditorSpace) {
        h = regionH - handleH - minEditorSpace;
      }
      const { max } = bottomHeightLimits(regionH);
      h = clamp(h, BOTTOM_COLLAPSE_THRESHOLD, max);
      return {
        ...prev,
        editorOpen: true,
        bottomPanelOpen: true,
        bottomHeight: h,
      };
    });
  }, []);

  // Force the bottom panel open with a safe, fixed height suitable for
  // the render progress view. This prevents the editor from being squashed
  // to empty when the render flow opens the dock.
  const forceOpenForRender = useCallback(() => {
    setLayout((prev) => {
      const regionH = editorRegionHeightRef.current || 800;
      const target = 300; // reliable size for progress + terminal
      const { min, max } = bottomHeightLimits(regionH);
      // Make sure bottom doesn't eat all the space - leave room for editor
      const safeMax = Math.max(min, Math.min(max, regionH - 200));
      const capped = Math.min(target, Math.max(200, Math.min(safeMax, 420)));
      return {
        ...prev,
        bottomPanelOpen: true,
        editorOpen: true,
        bottomHeight: clamp(capped, min, max),
      };
    });
  }, []);

  return {
    layout,
    setBottomPanelOpen,
    setContainerWidth,
    setEditorRegionHeight,
    setChatWidthFromPointer,
    setSidebarWidthFromPointer,
    resizeBottom,
    maximizeBottom,
    forceOpenForRender,
    setEditorOpen,
  };
}