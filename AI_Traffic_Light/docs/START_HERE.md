# Start Here — V035

V035 / `0_3_5` is the current candidate.

The V034 persistent-MJPEG direction is retained. V035 improves the weak points around it:

```text
Connect → status only
Start → config → start → persistent MJPEG
                 ↓
          exact multipart parser
                 ↓
          newest PC frame
                 ↓
       event-driven browser relay
```

If the ESP stream drops:

```text
status probe
  ↓
session still active? → reconnect stream
session lost/rebooted? → reapply config → start → reconnect
```

Retries use bounded exponential backoff.

For the ESP, replace only the `.ino` with the V035 file. Existing `secrets.h` does not change.
