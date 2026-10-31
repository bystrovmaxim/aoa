# Contract: UI

## Lifecycle diagram

| Situation | Shows |
|---|---|
| One, untouched | today's picture, plus the panel and hover |
| Diff, changes | union; green, amber, red dashed; unchanged grey and dim; signs `+ − ~` on elements; button with counts |
| Diff, nothing drawn changed | "no changes", drawn as in One |
| Row marked `+` | all green, dots too |
| Row marked `−` | all red and dashed |
| Not in the shown version | message and way back, no error |

Controls:

- **Click** on a marked state or transition: `DiffCard`. Outside or Escape closes.
- **Stepper** beside the version button, Shift + ↑ ↓, its list.
- **Panel**: Elements (kinds present) and, in Diff, Changes; 1-hop on at first; no gear shift, each mode having one thing to paint.
- **Hover**: an element, its transitions and what they reach stay lit; names only.
- **Address and room**: filters and paint are page settings; One's paint and Diff's kept apart.
- **Both directions**, left to right and top to bottom, in One and Diff.

## Left panel

| Row | Mark |
|---|---|
| Page only in B | `+` |
| Page only in A | `−` |
| Lifecycle in both, something in it changed | `~` |
| Any other | none |

Opening a lifecycle expands its domain, also for a row of one version.
