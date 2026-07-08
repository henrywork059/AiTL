import type { Detection } from "../types";

type Props = {
  detections: Detection[];
};

export function DetectionTable({ detections }: Props) {
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Class</th>
            <th>Confidence</th>
            <th>Box xyxy</th>
          </tr>
        </thead>
        <tbody>
          {detections.map((det) => (
            <tr key={det.id}>
              <td>{det.id}</td>
              <td>{det.class_name}</td>
              <td>{(det.confidence * 100).toFixed(1)}%</td>
              <td>{det.box_xyxy.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
