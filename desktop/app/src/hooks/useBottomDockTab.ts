import { useCallback, useEffect, useState } from "react";

import type { BottomDockTab, Settings } from "../api/types";

const STORAGE_KEY = "matemium-bottom-dock-tab";

function isBottomDockTab(value: string): value is BottomDockTab {
  return value === "progress" || value === "output";
}

function loadTab(defaultTab: BottomDockTab): BottomDockTab {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw && isBottomDockTab(raw)) return raw;
  } catch {
    // ignore
  }
  return defaultTab;
}

export function useBottomDockTab(settingsDefault: BottomDockTab = "progress") {
  const [tab, setTab] = useState<BottomDockTab>(() => loadTab(settingsDefault));

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, tab);
  }, [tab]);

  const selectTab = useCallback((next: BottomDockTab) => {
    setTab(next);
  }, []);

  const focusProgress = useCallback(() => {
    setTab("progress");
  }, []);

  return { tab, selectTab, focusProgress };
}

export function resolveBottomDockDefault(settings: Settings): BottomDockTab {
  return settings.bottomDockDefault === "output" ? "output" : "progress";
}