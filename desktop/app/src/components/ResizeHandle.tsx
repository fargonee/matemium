import { useEffect, useRef } from "react";

interface ResizeHandleProps {
  orientation: "horizontal" | "vertical";
  onDrag?: (delta: number) => void;
  onDragPosition?: (position: number) => void;
}

export function ResizeHandle({ orientation, onDrag, onDragPosition }: ResizeHandleProps) {
  const dragging = useRef(false);
  const lastPos = useRef(0);
  const onDragRef = useRef(onDrag);
  const onDragPositionRef = useRef(onDragPosition);

  useEffect(() => {
    onDragRef.current = onDrag;
  }, [onDrag]);

  useEffect(() => {
    onDragPositionRef.current = onDragPosition;
  }, [onDragPosition]);

  useEffect(() => {
    const handleMove = (event: MouseEvent) => {
      if (!dragging.current) return;
      const pos = orientation === "horizontal" ? event.clientY : event.clientX;
      if (onDragPositionRef.current) {
        onDragPositionRef.current(pos);
      } else if (onDragRef.current) {
        const delta = pos - lastPos.current;
        lastPos.current = pos;
        onDragRef.current(delta);
      }
    };

    const handleUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, [orientation]);

  const handleMouseDown = (event: React.MouseEvent) => {
    event.preventDefault();
    dragging.current = true;
    const pos = orientation === "horizontal" ? event.clientY : event.clientX;
    lastPos.current = pos;
    onDragPositionRef.current?.(pos);
    document.body.style.cursor =
      orientation === "horizontal" ? "row-resize" : "col-resize";
    document.body.style.userSelect = "none";
  };

  return (
    <div
      className={`resize-handle resize-handle-${orientation}`}
      onMouseDown={handleMouseDown}
      role="separator"
      aria-orientation={orientation}
      aria-label="Resize panel"
    />
  );
}