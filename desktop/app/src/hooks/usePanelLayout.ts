import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = "matemium-panel-layout";

export const BOTTOM_COLLAPSE_THRESHOLD = 48;
export const RESIZE_HANDLE_SIZE = 4;
export const MIN_MAIN_COLUMN_WIDTH = 240;

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
  bottomHeight: { min: BOTTOM_COLLAPSE_THRESHOLD, max: 520 },
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

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  }, [layout]);

  const setContainerWidth = useCallback((width: number) => {
    containerWidthRef.current = width;
    setLayout((prev) => fitLayoutToContainer(prev, width));
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
        bottomHeight: clamp(nextHeight, BOTTOM_COLLAPSE_THRESHOLD, LIMITS.bottomHeight.max),
      };
    });
  }, []);

  const setBottomPanelOpen = useCallback((open: boolean) => {
    setLayout((prev) => ({ ...prev, bottomPanelOpen: open }));
  }, []);

  return {
    layout,
    setBottomPanelOpen,
    setContainerWidth,
    setChatWidthFromPointer,
    setSidebarWidthFromPointer,
    resizeBottom,
  };
}