# Versioning

This project uses the underscore version style requested for the AI Traffic Light project.

## Version format

```text
0_0_0 = initial skeleton
0_0_1 = first patch
0_0_2 = second patch
0_1_0 = first larger functional milestone
1_0_0 = mature/major release
```

GitHub tags should use the same style with a `v` prefix:

```text
v0_0_0
v0_0_1
v0_1_0
```

## Current version history

```text
0_0_0  initial starter skeleton
0_0_1  documentation and version wording cleanup
```

## Recommended zip naming

```text
AI_Traffic_Light_0_0_0.zip
AI_Traffic_Light_0_0_1_doc_patch.zip
AI_Traffic_Light_0_0_2_patch.zip
AI_Traffic_Light_0_1_0.zip
```

## Commit message examples

```text
Initial project skeleton v0_0_0
Fix documentation versioning v0_0_1
Add mock live view API v0_0_2
Add webcam/video input v0_1_0
```

## Rule for future patches

Small fixes should increment the last number:

```text
0_0_1 → 0_0_2 → 0_0_3
```

Larger functional milestones should increment the middle number:

```text
0_0_x → 0_1_0 → 0_2_0
```
