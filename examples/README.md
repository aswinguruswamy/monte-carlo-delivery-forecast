# Examples

`sample_team.csv` is **made-up data** for the web page and the demo. It is not TAWOS data (D08), and no real person or project is in it.

- 117 done items from 2026-06-01 to 2026-09-30 (Story, Task, Improvement, Bug), on weekdays only.
- 6 open items (empty `Resolution_Date`).
- Columns: `Issue_Key`, `Type`, `Resolution_Date`, `Story_Point`.

Try it:

```bash
mcf forecast examples/sample_team.csv --backlog 40
```
