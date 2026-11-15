# Frontend

React + TypeScript + Vite + Tailwind single-page app for the game.
Docker Compose builds it and serves it with nginx, which also proxies `/api` to the backend (see the [main README](../README.md)).

| File (`src/`) | What it does |
|---|---|
| `App.tsx` | the game: questions, answers, reveal, wrong-guess recovery, "Who was it?" |
| `Explorer.tsx` | browse entities and their graph neighbourhood |
| `DevPanel.tsx` | developer view (`?dev=true`): candidates, probabilities, queries |
| `api.ts` | typed client for the backend API |

Local development against a running backend:

```bash
npm install
npm run dev      # Vite dev server
npm run build    # type-check and build to dist/
```
