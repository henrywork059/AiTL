# V016 acceptance checklist

V016 remains a candidate until the project owner explicitly confirms every required item.

1. Health/Dashboard report `0_1_6`.
2. Live AI long Active run / Default run identifiers remain inside the Trained model card.
3. Selected model Path and Run folder wrap inside the card without horizontal spillover.
4. Camera simulation starts and displays a vertical pedestrian crossing with horizontal white zebra bars.
5. Simulated pedestrians visibly travel top-to-bottom through the crossing.
6. Multiple simulated vehicles move horizontally across the road lanes.
7. The synthetic scene shows multiple pedestrians and visible variation over time.
8. Light / Normal / Busy density controls update the scene and reported status.
9. Pause scene freezes the current synthetic frame; Resume scene restarts frame progression.
10. A paused or moving simulation frame can still be captured by the existing Dataset Capture workflow.
11. Existing manual labeling and managed YOLO dataset generation still work on captured images.
12. Existing training page/status still loads without regression.
13. Existing trained-model discovery, selection, default, deletion, and live inference still work.
14. Confidence down to 1%, box/label toggles, and class filtering still work on Live AI.
15. Camera binary image responses preserve a request ID header.
16. Live AI remains prototype/simulation input only and does not control real public traffic infrastructure.
