# Research dashboard frontend

Start the backend on `127.0.0.1:8000` using the repository instructions, then run:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to the local FastAPI service. `npm run build` creates production files in `dist`; serving production requires routing `/api` to FastAPI and falling back to `index.html` for application routes.

```powershell
npm test
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

End-to-end tests require both local services and execute actual small Python simulations. `DASHBOARD_URL` overrides the browser base URL.

The application discovers all configuration schemas, model parameters, scenarios, limits, and optional integrations from the backend. Scientific calculations remain in Python. Charts load Plotly on demand, query bounded rows, preserve trials, and restrict observations to selected grid/model/variant cells. Full result exports remain available for offline analysis. Large chart queries show an explicit truncation notice.

Local theme preference is saved in browser storage. Configurations, run metadata, and results are persisted by the backend. Failed requests and unavailable metrics display explicit states.

The navigation registry in `src/App.tsx`, typed service in `src/api.ts`, and backend-discovered integration cards provide extension points for future modules. No wallets or blockchain connections are simulated.
