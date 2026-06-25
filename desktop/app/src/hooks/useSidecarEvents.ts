import { listen } from "@tauri-apps/api/event";
import { useEffect } from "react";

import type { SidecarEventPayload } from "../api/types";

export function useSidecarEvents(
  onEvent: (payload: SidecarEventPayload) => void,
): void {
  useEffect(() => {
    let unlisten: (() => void) | undefined;

    void listen<SidecarEventPayload>("sidecar-event", (event) => {
      onEvent(event.payload);
    }).then((fn) => {
      unlisten = fn;
    });

    return () => {
      unlisten?.();
    };
  }, [onEvent]);
}