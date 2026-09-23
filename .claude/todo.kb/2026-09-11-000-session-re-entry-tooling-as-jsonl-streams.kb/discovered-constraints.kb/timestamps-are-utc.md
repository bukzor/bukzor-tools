---
measured: 2026-09-10
session: f65fbdf3
---

# Record timestamps are UTC; the inventory prints local time

`timestamp` on every record is an ISO string in UTC. `claude-inventory`
renders local time through its `Clock`. An ad hoc index written on
2026-09-10 printed the raw strings and read as five hours off until
checked. Streams carry `time_ns`, which has no zone to misread, and local
time appears only where the humanizer renders it, which retires the class
of error.
