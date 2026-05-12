# Lumen UI

The Angular app in `frontend/` is a restrained, monochrome interface with a single indigo accent. Motion is reserved for state: cards easing in when content is ready, skeleton crossfades, short transitions on interactive surfaces, and tab changes. There is no decorative motion, no gradients in chrome, and no secondary accent colors.

## Component primitives

| Selector        | Role |
|-----------------|------|
| `lum-button`    | Primary, secondary, ghost; sizes; loading; `clicked` output |
| `lum-input`     | Label, helper, error; `valueChange` |
| `lum-textarea`  | Same; `textareaKeydown` for parent shortcuts |
| `lum-card`      | Title + projected body |
| `lum-badge`     | default, success, warning, error |
| `lum-skeleton`  | Shape placeholders |
| `lum-spinner`   | Inline busy |
| `lum-code-block`| Prism SQL + copy |
| `lum-toast-stack` | Global toasts via `ToastService` |

## Theme tokens

CSS variables live in `frontend/src/styles.css` under `:root` and `:root.dark`. Tailwind maps them in `tailwind.config.js` (for example `accent`, `bg`, `text-muted`). To change the accent, adjust `--color-accent` and `--color-accent-hover` in both themes and re-check contrast (WCAG AA) against `--color-bg` and `--color-text`.

## Architecture

Standalone components only: feature routes under `app/features/`, shared primitives under `app/components/`, HTTP and SSE in `LumenApiService`, theme in `ThemeService`. Lazy routes load Ask, Schema, and Benchmarks inside `AppShellComponent`. Production builds assume the API is reverse-proxied under `/api` (see `frontend/nginx.conf`).
