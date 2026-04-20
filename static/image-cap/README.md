# image-cap

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) 
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```
### Environment variables

Create `.env.local` in this folder (`static/image-cap`) and configure:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

> `VITE_API_BASE_URL` is used for backend APIs and image URLs. If omitted, it defaults to `http://127.0.0.1:8000`.
### Compile and Hot-Reload for Development

Run from this directory:

```sh
npm run dev -- --host 0.0.0.0 --port 5173
```

Or from the repo root:

```sh
npm --prefix ./static/image-cap run dev -- --host 0.0.0.0 --port 5173
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

## Testing Setup

This project now uses a layered frontend testing stack that matches common Vue hiring expectations:

- `Vitest` for unit and component tests
- `@testing-library/vue` and `@vue/test-utils` for component behavior
- `Playwright` for end-to-end browser tests
- `@vitest/coverage-v8` for coverage reports

Recommended commands:

```sh
npm run test:unit
npm run test:coverage
npm run test:e2e
```

Test directories:

- `tests/unit`: store and logic-focused tests
- `tests/component`: Vue component rendering and interaction tests
- `tests/e2e`: browser-level user journey smoke tests

## Python Backend Tests

The repo also contains a FastAPI backend, and this frontend workspace now includes a `pytest` setup for backend-focused functional tests with coverage.

Run with the project virtual environment:

```sh
E:\E\image-cap\.venv\Scripts\python.exe -m pytest
```

Coverage reports:

- terminal summary: missing lines shown after the run
- HTML report: `htmlcov/index.html`

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```
