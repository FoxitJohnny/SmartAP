# SmartAP Frontend

Modern web application for SmartAP invoice processing automation built with Next.js 15, React 18, and TypeScript.

## Tech Stack

- **Framework**: Next.js 15+ (App Router)
- **Language**: TypeScript 5.3+
- **Styling**: Tailwind CSS 4.0 + shadcn/ui
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query
- **Forms**: React Hook Form + Zod
- **API Client**: Axios

## Getting Started

### Prerequisites

- Node.js 20+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
├── components/             # React components
│   ├── ui/                # shadcn/ui components
│   └── providers.tsx      # App providers
├── lib/
│   ├── api/               # API client and configuration
│   └── utils.ts           # Utility functions
├── stores/                # Zustand state stores
│   ├── authStore.ts       # Authentication state
│   └── uiStore.ts         # UI state
├── types/                 # TypeScript type definitions
└── hooks/                 # Custom React hooks
```

## Phase 3.1 - Project Setup ✅

- [x] Next.js 15+ with App Router and TypeScript
- [x] Tailwind CSS + shadcn/ui components
- [x] React Query for data fetching
- [x] Zustand for state management
- [x] API client with authentication interceptors
- [x] Project structure and configuration

## Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
```

## Environment Variables

See `.env.example` for required environment variables.

## Learn More

To learn more about the technologies used:

- [Next.js Documentation](https://nextjs.org/docs)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Zustand Documentation](https://zustand-demo.pmnd.rs/)
- [shadcn/ui Documentation](https://ui.shadcn.com/)

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
