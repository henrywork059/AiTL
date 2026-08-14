import { useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { DatasetLabelBox, LabelClass } from "../types";

type Point = { x: number; y: number };

type Props = {
  imageUrl: string;
  width: number;
  height: number;
  classes: LabelClass[];
  selectedClassId: number;
  labels: DatasetLabelBox[];
  onChange: (labels: DatasetLabelBox[]) => void;
};

function orderedBox(start: Point, end: Point): [number, number, number, number] {
  return [
    Math.min(start.x, end.x),
    Math.min(start.y, end.y),
    Math.max(start.x, end.x),
    Math.max(start.y, end.y),
  ];
}

export function LabelingCanvas({
  imageUrl,
  width,
  height,
  classes,
  selectedClassId,
  labels,
  onChange,
}: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [dragStart, setDragStart] = useState<Point | null>(null);
  const [dragEnd, setDragEnd] = useState<Point | null>(null);

  function eventPoint(event: ReactPointerEvent<SVGSVGElement>): Point {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) return { x: 0, y: 0 };
    return {
      x: Math.max(0, Math.min(width, ((event.clientX - rect.left) / rect.width) * width)),
      y: Math.max(0, Math.min(height, ((event.clientY - rect.top) / rect.height) * height)),
    };
  }

  function startBox(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    const point = eventPoint(event);
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragStart(point);
    setDragEnd(point);
  }

  function moveBox(event: ReactPointerEvent<SVGSVGElement>) {
    if (!dragStart) return;
    setDragEnd(eventPoint(event));
  }

  function finishBox(event: ReactPointerEvent<SVGSVGElement>) {
    if (!dragStart) return;
    const end = eventPoint(event);
    const box = orderedBox(dragStart, end);
    setDragStart(null);
    setDragEnd(null);
    if (box[2] - box[0] < 3 || box[3] - box[1] < 3) return;
    const selectedClass = classes.find((item) => item.id === selectedClassId);
    if (!selectedClass) return;
    onChange([
      ...labels,
      {
        class_id: selectedClass.id,
        class_name: selectedClass.name,
        box_xyxy: box.map((value) => Math.round(value * 1000) / 1000) as [number, number, number, number],
      },
    ]);
  }

  const draftBox = dragStart && dragEnd ? orderedBox(dragStart, dragEnd) : null;

  return (
    <div className="label-canvas-shell">
      <svg
        ref={svgRef}
        className="label-canvas"
        viewBox={`0 0 ${width} ${height}`}
        onPointerDown={startBox}
        onPointerMove={moveBox}
        onPointerUp={finishBox}
        onPointerCancel={() => { setDragStart(null); setDragEnd(null); }}
        aria-label="Manual bounding-box labeling canvas"
      >
        <image href={imageUrl} x={0} y={0} width={width} height={height} preserveAspectRatio="none" />
        {labels.map((label, index) => {
          const [x1, y1, x2, y2] = label.box_xyxy;
          return (
            <g key={`${label.class_id}-${index}-${x1}-${y1}`}>
              <rect className="manual-label-box" x={x1} y={y1} width={x2 - x1} height={y2 - y1} />
              <text className="manual-label-text" x={x1 + 4} y={Math.max(14, y1 + 15)}>
                {index + 1}. {label.class_name}
              </text>
            </g>
          );
        })}
        {draftBox && (
          <rect
            className="manual-label-box draft"
            x={draftBox[0]}
            y={draftBox[1]}
            width={draftBox[2] - draftBox[0]}
            height={draftBox[3] - draftBox[1]}
          />
        )}
      </svg>
    </div>
  );
}
