# SkinGraph — Frontend

React 19 + TypeScript + Vite frontend for [SkinGraph](https://skin.anirudhdev.com).

## Stack

- **React 19** + **TypeScript** + **Vite 8**
- **react-router-dom v7** — client-side routing
- **@supabase/supabase-js** — auth + database
- **Capacitor** — Android app wrapper
- Deployed on **Cloudflare Pages**

## Pages

| Route | Page |
|---|---|
| `/` | Home — product input, label photo upload, skin type selector |
| `/results` | Results — score, ingredients, red flags, alternatives, compatibility |
| `/auth` | Sign in / Sign up (email + Google OAuth) |
| `/dashboard` | User dashboard — history, saved products, skin profile |

## Local dev

```bash
npm install
cp .env.example .env
# Edit .env with your values
npm run dev
```

## Environment variables

```
VITE_API_URL=https://skingraph-backend.onrender.com
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## Android

```bash
npm run cap:sync      # build + sync to Android project
npx cap open android  # open in Android Studio
```

## Scripts

| Script | Description |
|---|---|
| `npm run dev` | Local dev server |
| `npm run build` | Production build |
| `npm run cap:sync` | Build + sync to Android |
| `npx cap open android` | Open Android Studio |
