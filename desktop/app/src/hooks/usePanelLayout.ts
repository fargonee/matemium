import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = "matemium-panel-layout";

export const BOTTOM_COLLAPSE_THRESHOLD = 48;
export const RESIZE_HANDLE_SIZE = 4;
export const MIN_MAIN_COLUMN_WIDTH = 240;
export const MIN_EDITOR_STAGE_HEIGHT = 0;

export interface PanelLayout {
  sidebarWidth: number;
  chatWidth: number;
  bottomHeight: number;
  bottomPanelOpen: boolean;
}

const DEFAULT_LAYOUT: PanelLayout = {
  sidebarWidth: 260,
  chatWidth: 320,
  bottomHeight: 200,
  bottomPanelOpen: true,
};

type NumericLayoutKey = Exclude<keyof PanelLayout, "bottomPanelOpen">;

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
  // Allow the bottom dock panels to take the full available height (minus the resize handle bar itself).
  const max = Math.max(BOTTOM_COLLAPSE_THRESHOLD, regionHeight - RESIZE_HANDLE_SIZE);
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
        return { ...prev, bottomHeight: clamped };
      }
      return prev;
    });
  }, []);

  const setChatWidthFromPointer = useCallback((clientX: number, containerRight: number) => {
    // Pointer is on the 4px gutter column; chat column is everything to its right.
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
      const { max } = bottomHeightLimits(regionH);
      const nextHeight = prev.bottomHeight - delta;
      if (nextHeight < BOTTOM_COLLAPSE_THRESHOLD) {
        return {
          ...prev,
          bottomPanelOpen: false,
          bottomHeight: DEFAULT_LAYOUT.bottomHeight,
        };
      }
      return {
        ...prev,
        bottomHeight: clamp(nextHeight, BOTTOM_COLLAPSE_THRESHOLD, max),
      };
    });
  }, []);

  const setBottomPanelOpen = useCallback((open: boolean) => {
    setLayout((prev) => {
      if (!open) return { ...prev, bottomPanelOpen: false };
      const { min, max } = bottomHeightLimits(editorRegionHeightRef.current);
      // When opening (especially on Render to show progress), force a
      // reasonable fixed height so the main editor + viewport don't get
      // squashed to empty/zero. Use previous only if it was already a good size.
      const wasClosed = !prev.bottomPanelOpen;
      let h = prev.bottomHeight;
      if (wasClosed || h < 220) {
        h = 320; // sensible size for progress panel + logs
      }
      // Never let the dock eat the entire (or most of) the viewport on render start
      const reasonableMax = Math.min(max, 420);
      h = clamp(h, min, reasonableMax);
      return { ...prev, bottomPanelOpen: true, bottomHeight: h };
    });
  }, []);

  const maximizeBottom = useCallback(() => {
    setLayout((prev) => {
      const { max } = bottomHeightLimits(editorRegionHeightRef.current);
      return {
        ...prev,
        bottomPanelOpen: true,
        bottomHeight: max,
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
  };
}