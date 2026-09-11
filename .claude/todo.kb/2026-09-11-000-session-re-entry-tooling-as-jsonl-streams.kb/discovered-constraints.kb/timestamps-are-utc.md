---
measured: 2026-09-10
session: f65fbdf3
---

# Record timestamps are UTC; the inventory prints local time

`timestamp` on every record is an ISO string in UTC. `claude-inventory`
renders local time through its `Clock`. An ad hoc index written on
2026-09-10 printed the raw strings and read as five hours off until
checked. A stream that carries an epoch integer moves the conversion into
`jq` (`localtime`, `strflocaltime`) and retires the class of error.
