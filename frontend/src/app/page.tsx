import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      {/* Hero Section */}
      <div className="flex items-center justify-center p-4 pt-10">
        <div className="w-full max-w-4xl">
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
                AI-Powered Invoice Processing & Accounts Payable Automation{' '}
                <span className="text-primary font-semibold">with Foxit Technologies</span>
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
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Executive Summary — 2-column layout */}
      <div className="w-full max-w-7xl mx-auto px-4 py-10">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left Column */}
          <div className="space-y-6">
            {/* Executive Summary */}
            <Card className="border">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🏢</span>
                  <CardTitle className="text-xl">Executive Summary</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-muted-foreground leading-relaxed">
                <p>
                  SmartAP is an <strong className="text-foreground">AI-powered accounts payable (AP) automation platform</strong> designed
                  for SMEs and mid-market firms. It leverages Foxit APIs to transform the manual, error-prone process of invoice
                  handling into a streamlined, high-ROI digital workflow.
                </p>
                <p>
                  Manual invoice processing is a significant bottleneck for finance departments, leading to delayed payments and
                  increased risk of fraud. SmartAP automates the lifecycle of an invoice — from ingestion and data extraction to
                  reconciliation and final approval. By integrating Foxit&apos;s OCR and PDF technology with modern AI, SmartAP achieves
                  high Straight-Through Processing (STP) rates, allowing teams to focus on strategic financial planning rather
                  than data entry.
                </p>
              </CardContent>
            </Card>

            {/* Value Proposition */}
            <Card className="border">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">💎</span>
                  <CardTitle className="text-xl">Value Proposition</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 text-sm text-muted-foreground">
                  <ValueItem icon="💰" title="High ROI for Finance Departments">
                    Automates labor-intensive tasks like manual entry and reconciliation, leading to significant cost savings.
                  </ValueItem>
                  <ValueItem icon="⚡" title="High Straight-Through Processing (STP)">
                    Achieves a 95.5% rate of automated processing in prototype, minimizing the need for human intervention.
                  </ValueItem>
                  <ValueItem icon="🛡️" title="Reduced Financial Risk">
                    AI-powered detection flags potential fraud, duplicate billing, and discrepancies between invoices and purchase orders.
                  </ValueItem>
                  <ValueItem icon="🎯" title="Enhanced Data Accuracy">
                    Zero-shot extraction pulls line items and complex data automatically, reducing human error.
                  </ValueItem>
                  <ValueItem icon="📈" title="Scalability for Growth">
                    Tailored to meet the needs of SMEs and mid-market firms looking to professionalize their finance workflows.
                  </ValueItem>
                </ul>
              </CardContent>
            </Card>

            {/* Technical Core: The Foxit Advantage */}
            <Card className="border bg-blue-50/50 dark:bg-blue-950/20">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🔧</span>
                  <CardTitle className="text-xl">Technical Core: The Foxit Advantage</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  The application&apos;s intelligence is built on a foundation of high-performance document services:
                </p>
                <div className="space-y-3">
                  <div className="flex gap-3 items-start">
                    <div className="w-8 h-8 rounded-md bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center shrink-0 text-lg">📷</div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">Foxit OCR API</p>
                      <p className="text-xs text-muted-foreground">Converts scanned receipts and image-based PDFs into machine-readable text with high precision.</p>
                    </div>
                  </div>
                  <div className="flex gap-3 items-start">
                    <div className="w-8 h-8 rounded-md bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center shrink-0 text-lg">🤖</div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">Zero-Shot Data Extraction</p>
                      <p className="text-xs text-muted-foreground">AI automatically identifies and extracts line items, vendor details, and tax amounts without pre-defined templates.</p>
                    </div>
                  </div>
                  <div className="flex gap-3 items-start">
                    <div className="w-8 h-8 rounded-md bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center shrink-0 text-lg">📄</div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">PDF Flattening</p>
                      <p className="text-xs text-muted-foreground">Ensures document integrity and security by merging form fields and annotations before final archiving or payment.</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Open-Source Value Proposition */}
            <Card className="border">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🌐</span>
                  <CardTitle className="text-xl">Foxit Open-Source SmartAP</CardTitle>
                </div>
                <CardDescription className="text-xs">
                  Open-sourcing SmartAP serves as a powerful bridge between Foxit&apos;s high-performance technology and real-world business needs.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {/* Real-World Impact */}
                <div>
                  <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5 mb-2">
                    <span className="text-base">🏗️</span> Demonstrating Real-World Technology Impact
                  </h4>
                  <ul className="space-y-1.5 text-xs text-muted-foreground pl-6">
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">From Sample Code to Solutions:</strong> A complete blueprint for end-to-end workflows like invoice matching and automated approvals.</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Showcasing Performance:</strong> Foxit&apos;s high-fidelity rendering and fast parsing engines in action within a demanding enterprise environment.</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">AI Integration Evidence:</strong> Foxit AI performing complex tasks like zero-shot data extraction and risk mitigation in financial workflows.</span></li>
                  </ul>
                </div>

                {/* Business Innovation */}
                <div>
                  <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5 mb-2">
                    <span className="text-base">🚀</span> Accelerating Business Innovation &amp; Adoption
                  </h4>
                  <ul className="space-y-1.5 text-xs text-muted-foreground pl-6">
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Lowering Barriers to Entry:</strong> Businesses can start small with the open-source community version to test feasibility before migrating to enterprise-grade.</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Speed to Market:</strong> Developers can adapt the SmartAP codebase to their specific needs, significantly reducing build time from scratch.</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Cost Efficiency:</strong> Open-source frameworks can save firms up to 3.5× the cost of building from proprietary scratch.</span></li>
                  </ul>
                </div>

                {/* Trustworthy Ecosystem */}
                <div>
                  <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5 mb-2">
                    <span className="text-base">🤝</span> Building a Trustworthy &amp; Agile Ecosystem
                  </h4>
                  <ul className="space-y-1.5 text-xs text-muted-foreground pl-6">
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Transparency &amp; Security:</strong> Publicly available code invites community monitoring, helping identify and close security gaps faster.</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Flexibility &amp; Choice:</strong> Businesses are not locked-in to a single vendor&apos;s roadmap — they have freedom to modify and extend.</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Shaping the Future:</strong> Contributions from Finance, Healthcare, and Legal industries allow the technology to evolve based on actual user needs.</span></li>
                  </ul>
                </div>

                {/* Developer Community */}
                <div>
                  <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5 mb-2">
                    <span className="text-base">👩‍💻</span> Empowering the Developer Community
                  </h4>
                  <ul className="space-y-1.5 text-xs text-muted-foreground pl-6">
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Skill Development:</strong> Complete applications help developers master Foxit&apos;s multi-platform SDKs (Windows, Mac, Linux, Web, Android, iOS).</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Developer-Friendly Integration:</strong> Demonstrates how Foxit&apos;s REST APIs can be chained for low-code or no-code environments.</span></li>
                    <li className="flex gap-2"><span className="text-primary shrink-0">•</span><span><strong className="text-foreground">Access to Talent:</strong> Active open-source participation connects Foxit with a global pool of skilled developers passionate about document technology.</span></li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Phase 3.1 section below */}
        <div className="mt-8 max-w-4xl mx-auto">
          <Card className="border-2">
            <CardContent className="pt-6">
              <div className="border-t pt-6">
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
        </div>
      </div>
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

function ValueItem({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-3 items-start">
      <span className="text-lg shrink-0">{icon}</span>
      <div>
        <p className="text-sm font-semibold text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground">{children}</p>
      </div>
    </li>
  );
}

