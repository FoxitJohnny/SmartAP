import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
      <main className="w-full max-w-4xl">
        <Card className="border-2">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto w-20 h-20 bg-primary rounded-lg flex items-center justify-center">
              <svg
                className="w-12 h-12 text-primary-foreground"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <CardTitle className="text-4xl font-bold tracking-tight">
              SmartAP
            </CardTitle>
            <CardDescription className="text-lg">
              AI-Powered Invoice Processing & Accounts Payable Automation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <FeatureCard
                icon="📄"
                title="Invoice Processing"
                description="Automated data extraction from invoices using AI"
              />
              <FeatureCard
                icon="🔍"
                title="PO Matching"
                description="Intelligent 3-way matching with purchase orders"
              />
              <FeatureCard
                icon="🛡️"
                title="Risk Detection"
                description="Fraud detection and duplicate invoice prevention"
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <Link href="/login">
                <Button size="lg" className="text-base w-full sm:w-auto">
                  Get Started
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="text-base">
                View Documentation
              </Button>
            </div>

            <div className="pt-6 border-t">
              <h3 className="font-semibold text-sm text-muted-foreground mb-3 text-center">
                Phase 3.1 - Project Setup Complete ✅
              </h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center gap-2">
                  <span className="text-green-500">✓</span>
                  Next.js 15+ with App Router and TypeScript
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-500">✓</span>
                  React Query for data fetching and caching
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-500">✓</span>
                  Zustand for state management
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-500">✓</span>
                  shadcn/ui components with Tailwind CSS
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-green-500">✓</span>
                  API client with authentication
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <Card>
      <CardHeader>
        <div className="text-4xl mb-2">{icon}</div>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription>{description}</CardDescription>
      </CardContent>
    </Card>
  );
}

