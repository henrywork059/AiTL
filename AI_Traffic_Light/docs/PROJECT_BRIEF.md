# Project Brief

## Project name

**AI Vision-Based Adaptive Traffic Light System**

## Problem

Traditional traffic lights usually operate using fixed timing or limited sensor input. They may not respond well to real-time pedestrian demand, vehicle queues, slow crossing pedestrians, or unusual road conditions.

## Proposed solution

Use a camera-based computer vision system to detect and count pedestrians and vehicles. The system then estimates traffic demand and simulates adaptive traffic-light decisions.

## Student-scale goal

This project is a prototype and demonstration system. It should simulate or control a model traffic light, not a real public road traffic signal.

## Core functions

- Detect pedestrians.
- Detect vehicles.
- Count objects in predefined traffic zones.
- Estimate pedestrian demand.
- Estimate vehicle queue demand.
- Extend pedestrian green when people are waiting or crossing.
- Extend vehicle green when vehicle queue is high and pedestrian demand is low.
- Show live visualization in a GUI.
- Capture data for future model training.

## Initial object classes

- person
- car
- bus
- truck
- motorcycle
- bicycle

## Future functions

- Slow-crossing pedestrian detection.
- Wheelchair-like object / stroller / large group warning.
- Multiple camera inputs.
- Instance segmentation.
- Physical LED traffic-light model.
- Model training and export workflow.
