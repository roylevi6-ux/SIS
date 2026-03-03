'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Separator } from '@/components/ui/separator';
import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  BookOpen,
  Brain,
  ShieldAlert,
  Layers,
  Target,
  Users,
  Gauge,
  ArrowUp,
  Globe,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Table of Contents navigation
// ---------------------------------------------------------------------------

const TOC_ITEMS = [
  { id: 'research', label: 'Sales Methodology Research', icon: BookOpen },
  { id: 'health-score', label: 'Health Score System', icon: Brain },
  { id: 'buying-cultures', label: 'Buying Culture Profiles', icon: Globe },
  { id: 'stages', label: 'Deal Stages, Exit Criteria & Objectives', icon: Layers },
  { id: 'forecast', label: 'Forecast Categories', icon: Target },
  { id: 'agents', label: 'Active Agents & Roles', icon: Users },
  { id: 'never-rules', label: 'NEVER Rules (Hard Guardrails)', icon: ShieldAlert },
  { id: 'confidence-penalties', label: 'Confidence Penalties', icon: Gauge },
];

// ---------------------------------------------------------------------------
// Scroll spy hook — tracks which section is currently visible
// ---------------------------------------------------------------------------

function useScrollSpy(sectionIds: string[]) {
  const [activeId, setActiveId] = useState<string>(sectionIds[0] ?? '');

  useEffect(() => {
    const elements = sectionIds
      .map((id) => document.getElementById(id))
      .filter(Boolean) as HTMLElement[];

    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Find the topmost visible section
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          setActiveId(visible[0].target.id);
        }
      },
      {
        // Section is "active" when its top is in the upper 30% of viewport
        rootMargin: '-20% 0px -70% 0px',
        threshold: 0,
      }
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [sectionIds]);

  return activeId;
}

// ---------------------------------------------------------------------------
// Desktop TOC — sticky right-rail with scroll spy active state
// ---------------------------------------------------------------------------

function TableOfContents({ activeId }: { activeId: string }) {
  const handleClick = useCallback((id: string) => {
    const target = document.getElementById(id);
    if (target) {
      target.setAttribute('tabindex', '-1');
      target.focus({ preventScroll: true });
    }
  }, []);

  return (
    <nav aria-label="On this page" className="max-h-[calc(100vh-6rem)] overflow-y-auto">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
        On this page
      </p>
      <div className="flex flex-col gap-0.5">
        {TOC_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeId === item.id;
          return (
            <a
              key={item.id}
              href={`#${item.id}`}
              data-toc-id={item.id}
              aria-current={isActive ? 'page' : undefined}
              onClick={() => handleClick(item.id)}
              className={cn(
                'flex items-center gap-2 py-1.5 text-sm transition-colors duration-150',
                isActive
                  ? 'border-l-2 border-primary pl-3 text-foreground font-medium'
                  : 'pl-3.5 text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon className="size-3.5 shrink-0" />
              <span className="line-clamp-1">{item.label}</span>
            </a>
          );
        })}
      </div>
      {/* Back to top */}
      <a
        href="#top"
        className="flex items-center gap-2 mt-4 pt-3 border-t pl-3.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowUp className="size-3 shrink-0" />
        Back to top
      </a>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Mobile TOC — sticky collapsible bar showing current section
// ---------------------------------------------------------------------------

function MobileToc({ activeId }: { activeId: string }) {
  const [open, setOpen] = useState(false);
  const activeItem = TOC_ITEMS.find((item) => item.id === activeId) ?? TOC_ITEMS[0];
  const ActiveIcon = activeItem.icon;

  const handleClick = useCallback((id: string) => {
    setOpen(false);
    const target = document.getElementById(id);
    if (target) {
      target.setAttribute('tabindex', '-1');
      target.focus({ preventScroll: true });
    }
  }, []);

  return (
    <div className="xl:hidden sticky top-0 z-30 bg-background/95 backdrop-blur border-b -mx-4 sm:-mx-6 px-4 sm:px-6">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full py-2.5 text-sm"
        aria-expanded={open}
        aria-controls="mobile-toc-list"
      >
        <span className="flex items-center gap-2 font-medium text-foreground">
          <ActiveIcon className="size-4 text-primary shrink-0" />
          {activeItem.label}
        </span>
        {open ? (
          <ChevronUp className="size-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="size-4 text-muted-foreground" />
        )}
      </button>
      {open && (
        <nav id="mobile-toc-list" aria-label="On this page" className="pb-2">
          {TOC_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeId === item.id;
            return (
              <a
                key={item.id}
                href={`#${item.id}`}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => handleClick(item.id)}
                className={cn(
                  'flex items-center gap-2 py-2 px-2 text-sm rounded-md transition-colors',
                  isActive
                    ? 'text-foreground bg-muted font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                )}
              >
                <Icon className="size-3.5 shrink-0" />
                {item.label}
              </a>
            );
          })}
        </nav>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Collapsible section wrapper
// ---------------------------------------------------------------------------

function Section({
  id,
  title,
  icon: Icon,
  children,
  defaultOpen = true,
}: {
  id: string;
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section id={id} className="scroll-mt-16 xl:scroll-mt-6">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-3 py-2 group">
          <Icon className="size-5 text-primary shrink-0" />
          <h2 className="text-lg font-semibold tracking-tight text-left">{title}</h2>
          <div className="flex-1" />
          {open ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="pl-4 sm:pl-8 pb-6 space-y-4 min-w-0 overflow-hidden">{children}</div>
        </CollapsibleContent>
      </Collapsible>
      <Separator />
    </section>
  );
}


// ---------------------------------------------------------------------------
// Section 1 — Sales Methodology Research
// ---------------------------------------------------------------------------

const RESEARCH_FRAMEWORKS = [
  {
    framework: 'MEDDIC / MEDDPICC',
    keyPrinciple: 'Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion, Competition.',
    sisImpact: 'Core pillars adopted — Economic Buyer engagement (Agent 6), Champion identification (Agent 2), Decision Process mapping (Agent 7 MSP). MEDDPICC adds Paper Process and Competition, both captured.',
    role: 'Primary influence',
  },
  {
    framework: 'SPICED (Winning by Design)',
    keyPrinciple: 'Situation, Pain, Impact, Critical Event, Decision.',
    sisImpact: 'Informed emphasis on buyer-validated pain (weighted highest at 14%) and compelling events / urgency (10%). "Critical Event" maps to catalyst analysis in Agent 8.',
    role: 'Secondary influence',
  },
  {
    framework: 'Challenger Sale',
    keyPrinciple: 'Teach-Tailor-Take Control.',
    sisImpact: 'Influenced momentum analysis: we measure whether the buyer is driving the deal forward (positive) vs. the seller doing all the pushing (negative). Agent 4 distinguishes buyer-initiated vs. seller-initiated engagement.',
    role: 'Behavioral influence',
  },
  {
    framework: 'Force Management / Command of the Message',
    keyPrinciple: 'Required Business Capabilities, Positive Business Outcomes, Required Capabilities.',
    sisImpact: 'Reinforced that pain must be buyer-articulated, not seller-projected. Agent 3 (Commercial) checks whether ROI and value narratives originate from buyer statements vs. seller pitches.',
    role: 'Validation principle',
  },
  {
    framework: 'Sandler Selling System',
    keyPrinciple: 'Pain, Budget, Decision.',
    sisImpact: 'Contributed the idea that budget authority must be verified through behavior, not assumed from title. Agent 6 (Economic Buyer) requires direct engagement evidence — secondhand mentions do not count.',
    role: 'Verification principle',
  },
];

function ResearchSection() {
  return (
    <Section id="research" title="Sales Methodology Research" icon={BookOpen}>
      <Card>
        <CardContent className="pt-4 space-y-4 text-sm leading-relaxed">
          <div>
            <h3 className="font-semibold mb-1">Why we built a custom health score</h3>
            <p className="text-muted-foreground">
              SIS was designed for Riskified&apos;s enterprise sales cycles, which are long (6-18 months),
              multi-threaded, and involve complex buying committees. Off-the-shelf CRM scoring (e.g.
              Salesforce &quot;Opportunity Score&quot;) relies on rep-entered stage data and simple heuristics
              that fail for deals of this complexity.
            </p>
          </div>

          <div>
            <h3 className="font-semibold mb-1">Frameworks evaluated</h3>
            <div className="overflow-x-auto">
              <Table className="table-fixed w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[22%] whitespace-normal">Framework</TableHead>
                    <TableHead className="w-[24%] whitespace-normal">Key Principle</TableHead>
                    <TableHead className="whitespace-normal">SIS Impact</TableHead>
                    <TableHead className="w-[16%] whitespace-normal">Role</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {RESEARCH_FRAMEWORKS.map((fw) => (
                    <TableRow key={fw.framework}>
                      <TableCell className="text-xs font-medium align-top whitespace-normal break-words">{fw.framework}</TableCell>
                      <TableCell className="text-xs text-muted-foreground whitespace-normal align-top break-words">{fw.keyPrinciple}</TableCell>
                      <TableCell className="text-xs text-muted-foreground whitespace-normal align-top break-words">{fw.sisImpact}</TableCell>
                      <TableCell className="align-top">
                        <Badge variant="outline" className="text-xs whitespace-normal break-words">{fw.role}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-1">Key design decisions</h3>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li><strong>Transcript-only analysis:</strong> We deliberately exclude CRM stage data to avoid rep bias. Stage is inferred from conversation content by Agent 1.</li>
              <li><strong>Anti-sycophancy guardrails:</strong> Every agent prompt includes explicit instructions to measure the <em>buyer</em>, not validate the seller&apos;s optimism.</li>
              <li><strong>Adversarial validation:</strong> Agent 9 exists solely to challenge the most optimistic findings from Agents 1-8, inspired by red-team practices in intelligence analysis.</li>
              <li><strong>Evidence-chain requirements:</strong> All pricing numbers must trace to verbatim transcript quotes. No inferred or hallucinated figures.</li>
              <li><strong>Champion &gt; Stakeholder count:</strong> We split the original &quot;Stakeholder Completeness&quot; weight into Champion Strength (12%) and Multi-threading (7%) after research showed champion presence is the #1 predictor of deal outcomes.</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Section 2 — Health Score System
// ---------------------------------------------------------------------------

const HEALTH_SCORE_COMPONENTS = [
  {
    component: 'Buyer-Validated Pain & Commercial Clarity',
    weight: 14,
    source: 'Agent 3 (Commercial), Agent 9 (Adversarial)',
    description: 'Is the pain buyer-articulated? Is there pricing clarity and ROI alignment? Agent 3 extracts commercial signals; Agent 9 validates they are evidence-backed.',
    expectedFrom: 'All stages',
  },
  {
    component: 'Momentum Quality',
    weight: 13,
    source: 'Agent 4 (Momentum)',
    description: 'Is buying energy increasing, stable, or fading? Measures buyer-initiated engagement, cadence trends, topic progression, and action completion.',
    expectedFrom: 'All stages',
  },
  {
    component: 'Champion Strength',
    weight: 12,
    source: 'Agent 2 (Relationship)',
    description: 'Has a champion been identified showing advocacy behavior: stakeholder introductions, follow-up ownership, "we" language, internal process navigation? Friendliness alone does not qualify.',
    expectedFrom: 'Stage 3+',
  },
  {
    component: 'Commitment Quality',
    weight: 11,
    source: 'Agent 7 (MSP & Next Steps)',
    description: 'Are there buyer-confirmed next steps with dates, owners, and deliverables? Is there a mutual success plan? Tracks specificity escalation or decline across calls.',
    expectedFrom: 'Stage 5+',
  },
  {
    component: 'Economic Buyer Engagement',
    weight: 11,
    source: 'Agent 6 (Economic Buyer)',
    description: 'Has someone with budget authority engaged? Scored progressively: Direct-Active (full credit) > Direct-Passive > Champion-Relayed > Secondhand-Vague > No evidence.',
    expectedFrom: 'Stage 4+',
  },
  {
    component: 'Urgency & Compelling Event',
    weight: 10,
    source: 'Agents 4, 7, 8, 9',
    description: 'Is there a real catalyst forcing a decision? Existential (fraud spike) > Structural (platform migration) > Cosmetic (exploratory RFP). No catalyst = buyer can always delay.',
    expectedFrom: 'Stage 4+',
  },
  {
    component: 'Stage Appropriateness',
    weight: 9,
    source: 'Agent 1 (Stage)',
    description: 'Is the deal progressing through stages as expected? Detects stage regression (e.g. pricing renegotiation in a late-stage deal) and stalls.',
    expectedFrom: 'All stages',
  },
  {
    component: 'Multi-threading & Stakeholder Coverage',
    weight: 7,
    source: 'Agent 2 (Relationship)',
    description: 'Are multiple departments engaged (Payments, Fraud, Finance, IT, Legal, Procurement)? Is the deal single-threaded through one contact or properly multi-threaded?',
    expectedFrom: 'Stage 3+',
  },
  {
    component: 'Competitive Position',
    weight: 7,
    source: 'Agent 8 (Competitive)',
    description: 'What is the buyer replacing? How attached are they to the status quo? Is there a no-decision risk? Tracks competitor mentions, displacement barriers, and catalyst strength.',
    expectedFrom: 'Stage 3+',
  },
  {
    component: 'Technical Path Clarity',
    weight: 6,
    source: 'Agent 5 (Technical)',
    description: 'Is the integration technically feasible? Are technical stakeholders engaged? Tracks platform/stack details, POC progress, and technical blockers.',
    expectedFrom: 'Stage 5+',
  },
];

function HealthScoreSection() {
  return (
    <Section id="health-score" title="Health Score System" icon={Brain}>
      {/* Scoring Philosophy */}
      <Card className="border-l-4 border-l-primary">
        <CardContent className="pt-4 text-sm text-muted-foreground space-y-2">
          <p className="font-medium text-foreground">Scoring Philosophy</p>
          <p>
            The Health Score measures deal <strong>quality at its current stage</strong> &mdash; not progress through the pipeline.
            A Stage 1 deal with excellent discovery, clear next steps, and strong buyer engagement is Healthy.
            A Stage 5 deal missing basic qualification signals Needs Attention.
            Each deal is evaluated against what&apos;s expected at its stage, using evidence from call transcripts.
          </p>
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">
        The health score is a weighted composite of 10 components (11 for expansion deals), each derived from specialized agent analysis.
        Total weights sum to 100. Components are scored based on evidence strength, with stage-aware baselines for missing evidence.
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[24%] whitespace-normal">Component</TableHead>
                  <TableHead className="w-[6%] text-right whitespace-normal">Wt.</TableHead>
                  <TableHead className="w-[10%] whitespace-normal">Expected From</TableHead>
                  <TableHead className="w-[15%] whitespace-normal">Source Agent(s)</TableHead>
                  <TableHead className="whitespace-normal">What it measures</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {HEALTH_SCORE_COMPONENTS.map((row) => (
                  <TableRow key={row.component}>
                    <TableCell className="text-xs font-medium align-top whitespace-normal break-words">{row.component}</TableCell>
                    <TableCell className="text-xs text-right tabular-nums font-semibold align-top">{row.weight}%</TableCell>
                    <TableCell className="text-xs align-top whitespace-normal">
                      <Badge variant={row.expectedFrom === 'All stages' ? 'secondary' : 'outline'} className="text-[10px]">
                        {row.expectedFrom}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground align-top whitespace-normal break-words">{row.source}</TableCell>
                    <TableCell className="text-xs text-muted-foreground align-top whitespace-normal break-words">{row.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Champion absent ceiling</p>
            <p className="text-2xl font-bold tabular-nums">75 <span className="text-sm font-normal text-muted-foreground">at S3+</span></p>
            <p className="text-xs text-muted-foreground mt-1">Max health score when no champion identified (Stage 3+). No cap at Stage 1-2.</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">EB absent ceiling</p>
            <p className="text-2xl font-bold tabular-nums">80 <span className="text-sm font-normal text-muted-foreground">at S4+</span></p>
            <p className="text-xs text-muted-foreground mt-1">Max health score when no EB engagement (Stage 4+). No cap at Stage 1-3.</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Sparse data ceiling</p>
            <p className="text-2xl font-bold tabular-nums">60%</p>
            <p className="text-xs text-muted-foreground mt-1">Max confidence when fewer than 3 transcripts analyzed</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">Expansion Deal Adjustments</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 text-sm text-muted-foreground space-y-2">
          <p>
            Expansion deals (upsell, cross-sell within existing accounts) use a modified weight distribution
            that adds <strong>Account Relationship Health</strong> (13%) and adjusts other weights to reflect
            the different dynamics of selling to existing customers:
          </p>
          <ul className="list-disc list-inside space-y-1">
            <li>Account Relationship Health: 13% (new &mdash; from Agent 0E)</li>
            <li>Buyer-validated pain: 12% (vs. 14% for new logo)</li>
            <li>Technical path clarity: 9% (vs. 6% for new logo &mdash; integration is already proven)</li>
            <li>Competitive position: 4% (vs. 7% for new logo &mdash; incumbent advantage)</li>
            <li>Strained/Critical relationship caps health at 60</li>
            <li>Commit requires Strong or Adequate relationship status</li>
          </ul>
        </CardContent>
      </Card>

      {/* Stage-Aware Baselines */}
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">Stage-Aware Baselines</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-3">
          <p className="text-sm text-muted-foreground">
            Not all components matter equally at every stage. When a component isn&apos;t expected yet
            (e.g., Economic Buyer at Stage 1), missing evidence receives a <strong>neutral midpoint score</strong> &mdash;
            not a penalty. When a component IS expected and evidence is missing, that&apos;s a real gap.
          </p>

          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40%] whitespace-normal">Scenario</TableHead>
                  <TableHead className="whitespace-normal">Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="text-xs align-top whitespace-normal">Evidence present (positive)</TableCell>
                  <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">Scored on merit (full range)</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="text-xs align-top whitespace-normal">Evidence present (negative)</TableCell>
                  <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">Scored on merit (low range)</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="text-xs align-top whitespace-normal">Evidence missing &mdash; component expected at this stage</TableCell>
                  <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">Low (1-2 pts, ~10-18% of max)</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="text-xs align-top whitespace-normal">Evidence missing &mdash; component NOT expected at this stage</TableCell>
                  <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">Neutral midpoint (see table below)</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <p className="text-xs font-medium text-foreground mt-3">Neutral midpoint scores by component:</p>
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[45%] whitespace-normal">Component (Max)</TableHead>
                  <TableHead className="w-[20%] text-center whitespace-normal">Neutral Score</TableHead>
                  <TableHead className="whitespace-normal">Expected At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[
                  { name: 'Champion (12)', neutral: '5', expected: 'Stage 3+' },
                  { name: 'Commitment (11)', neutral: '5', expected: 'Stage 5+' },
                  { name: 'Economic Buyer (11)', neutral: '4', expected: 'Stage 4+' },
                  { name: 'Urgency (10)', neutral: '4', expected: 'Stage 4+' },
                  { name: 'Multi-threading (7)', neutral: '3', expected: 'Stage 3+' },
                  { name: 'Competitive (7)', neutral: '3', expected: 'Stage 3+' },
                  { name: 'Technical Path (6)', neutral: '3', expected: 'Stage 5+' },
                ].map((row) => (
                  <TableRow key={row.name}>
                    <TableCell className="text-xs align-top whitespace-normal">{row.name}</TableCell>
                    <TableCell className="text-xs text-center font-semibold tabular-nums align-top">{row.neutral}</TableCell>
                    <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">{row.expected}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground italic">
            Components always expected (Pain, Momentum, Stage Fit, Account Health) have no neutral baseline &mdash;
            they are scored on merit or penalized when missing at any stage.
          </p>
        </CardContent>
      </Card>

      {/* Stage-Aware Health Points Matrix */}
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">Stage-Aware Health Points &mdash; Missing Evidence Impact</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-3">
          <p className="text-sm text-muted-foreground">
            This matrix shows how each component is scored <strong>when evidence is missing</strong> at each deal stage.
            When evidence IS present (positive or negative), the component is always scored on merit regardless of stage.
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded bg-emerald-500/15 border border-emerald-500/30" />
              Neutral &mdash; not expected yet, no penalty
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded bg-red-500/15 border border-red-500/30" />
              Gap &mdash; expected at this stage, penalized
            </span>
          </div>

          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[28%] whitespace-normal">Component (Max)</TableHead>
                  <TableHead className="text-center whitespace-normal">S1</TableHead>
                  <TableHead className="text-center whitespace-normal">S2</TableHead>
                  <TableHead className="text-center whitespace-normal">S3</TableHead>
                  <TableHead className="text-center whitespace-normal">S4</TableHead>
                  <TableHead className="text-center whitespace-normal">S5</TableHead>
                  <TableHead className="text-center whitespace-normal">S6</TableHead>
                  <TableHead className="text-center whitespace-normal">S7</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[
                  { name: 'Pain & Commercial (14)', expectedAt: 1, neutral: null },
                  { name: 'Momentum (13)', expectedAt: 1, neutral: null },
                  { name: 'Champion (12)', expectedAt: 3, neutral: 5 },
                  { name: 'Commitment (11)', expectedAt: 5, neutral: 5 },
                  { name: 'Economic Buyer (11)', expectedAt: 4, neutral: 4 },
                  { name: 'Urgency (10)', expectedAt: 4, neutral: 4 },
                  { name: 'Stage Fit (9)', expectedAt: 1, neutral: null },
                  { name: 'Multi-threading (7)', expectedAt: 3, neutral: 3 },
                  { name: 'Competitive (7)', expectedAt: 3, neutral: 3 },
                  { name: 'Technical Path (6)', expectedAt: 5, neutral: 3 },
                ].map((row) => (
                  <TableRow key={row.name}>
                    <TableCell className="text-xs font-medium align-top whitespace-normal">{row.name}</TableCell>
                    {[1, 2, 3, 4, 5, 6, 7].map((stage) => {
                      const isExpected = stage >= row.expectedAt;
                      const label = isExpected ? '1-2' : String(row.neutral);
                      return (
                        <TableCell key={stage} className="text-center align-top p-1.5">
                          <span className={cn(
                            'inline-flex items-center justify-center h-7 w-full rounded text-xs font-semibold tabular-nums',
                            isExpected
                              ? 'bg-red-500/10 text-red-700 dark:text-red-400'
                              : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                          )}>
                            {label}
                          </span>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground italic">
            Green cells: component not yet expected &mdash; missing evidence scores at a neutral midpoint (no penalty).
            Red cells: component expected at this stage &mdash; missing evidence scores 1-2 points (~10-18% of max).
          </p>
        </CardContent>
      </Card>

      {/* Health Tiers */}
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">Health Tiers</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[20%] whitespace-normal">Tier</TableHead>
                  <TableHead className="w-[15%] whitespace-normal">Range</TableHead>
                  <TableHead className="whitespace-normal">Meaning</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="text-xs font-medium align-top">
                    <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Healthy</span>
                  </TableCell>
                  <TableCell className="text-xs tabular-nums align-top">70 &ndash; 100</TableCell>
                  <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">Deal shows strong signals for its current stage</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="text-xs font-medium align-top">
                    <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> Neutral</span>
                  </TableCell>
                  <TableCell className="text-xs tabular-nums align-top">40 &ndash; 69</TableCell>
                  <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">Deal is progressing normally; some areas need development</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="text-xs font-medium align-top">
                    <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-red-500" /> Needs Attention</span>
                  </TableCell>
                  <TableCell className="text-xs tabular-nums align-top">0 &ndash; 39</TableCell>
                  <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">Significant gaps or risks identified that require action</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Methodology Foundations */}
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">Methodology Foundations</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-2">
          <p className="text-sm text-muted-foreground">
            The SIS scoring system draws from five established sales methodologies:
          </p>
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[25%] whitespace-normal">Framework</TableHead>
                  <TableHead className="whitespace-normal">How It Informs SIS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[
                  { fw: 'MEDDIC/MEDDPICC', impact: 'Economic Buyer and Champion identification as progressive discovery, not binary checkboxes' },
                  { fw: 'Challenger Sale', impact: 'Seller-initiated engagement valued as teaching moments, not penalized' },
                  { fw: 'SPICED', impact: 'Stage-appropriate pain and impact expectations' },
                  { fw: 'Sandler Pain Funnel', impact: 'Champion signals recognized through observable behavior (intros, follow-ups, "we" language)' },
                  { fw: 'Force Management', impact: 'Competitive and technical validation as late-stage activities' },
                ].map((row) => (
                  <TableRow key={row.fw}>
                    <TableCell className="text-xs font-medium align-top whitespace-normal">{row.fw}</TableCell>
                    <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">{row.impact}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Section 2b — Buying Culture Profiles
// ---------------------------------------------------------------------------

const BUYING_CULTURE_WEIGHTS = [
  { component: 'Buyer-Validated Pain & Commercial Clarity', direct: 14, proxy: 14, differs: false },
  { component: 'Momentum Quality', direct: 13, proxy: 13, differs: false },
  { component: 'Champion Strength', direct: 12, proxy: 19, differs: true },
  { component: 'Commitment Quality', direct: 11, proxy: 11, differs: false },
  { component: 'Economic Buyer Engagement', direct: 11, proxy: 0, differs: true },
  { component: 'Urgency / Compelling Event', direct: 10, proxy: 10, differs: false },
  { component: 'Stage Appropriateness', direct: 9, proxy: 9, differs: false },
  { component: 'Multithreading / Stakeholder Coverage', direct: 7, proxy: 11, differs: true },
  { component: 'Competitive Position', direct: 7, proxy: 7, differs: false },
  { component: 'Technical Path Clarity', direct: 6, proxy: 6, differs: false },
];

function BuyingCultureSection() {
  return (
    <Section id="buying-cultures" title="Buying Culture Profiles" icon={Globe}>
      <p className="text-sm text-muted-foreground">
        Health score weights adjust based on regional buying patterns. In markets where economic buyers
        delegate entirely to a trusted internal proxy, measuring direct EB engagement would unfairly penalize
        deals that are actually well-structured. SIS applies culture-aware weight profiles so assessments
        reflect how decisions are actually made in each region.
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="whitespace-normal">Component</TableHead>
                  <TableHead className="w-[12%] text-right whitespace-normal">Direct</TableHead>
                  <TableHead className="w-[22%] text-right whitespace-normal">Proxy-Delegated (APAC)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {BUYING_CULTURE_WEIGHTS.map((row) => (
                  <TableRow
                    key={row.component}
                    className={row.differs ? 'bg-amber-50 dark:bg-amber-950/20' : undefined}
                  >
                    <TableCell className="text-xs font-medium align-top whitespace-normal break-words">
                      {row.component}
                    </TableCell>
                    <TableCell className="text-xs text-right tabular-nums font-semibold align-top">
                      {row.direct}
                    </TableCell>
                    <TableCell className="text-xs text-right tabular-nums font-semibold align-top">
                      {row.proxy}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground italic">
        Proxy-Delegated applies to Japan, China, and Korea where the economic buyer typically delegates
        entirely to a trusted proxy and rarely appears on recorded calls.
      </p>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Section 3 — Deal Stages
// ---------------------------------------------------------------------------

const STAGES = [
  {
    number: 1,
    name: 'Qualify',
    duration: 'Months',
    objective: 'AE dives deeper after BD handoff — refine use case, validate fit, identify decision drivers, validate contacts.',
    exitCriteria: [
      'Use case clearly articulated and documented',
      'Market/vertical fit validated',
      'Key decision drivers identified',
      'Primary contacts confirmed and engaged',
      'NDA executed (if required)',
    ],
    keySignals: 'Use case discussion, market/vertical fit, NDA mentions, BD-to-AE handoff references.',
  },
  {
    number: 2,
    name: 'Establish Business Case',
    duration: '2-6 weeks',
    objective: 'Build ROI framework, CPQ configuration. Business case documented with measurable value.',
    exitCriteria: [
      'Business case documented with measurable value',
      'ROI framework built and presented',
      'Data exports and order volume analysis completed',
      'Chargeback rates and financial impact quantified',
    ],
    keySignals: 'Data exports, order volume analysis, chargeback rate discussion, ROI calculations.',
  },
  {
    number: 3,
    name: 'Scope',
    duration: '4-12 weeks',
    objective: 'Refine value proposition, demonstrate technology advantages, draft quote, run pilots.',
    exitCriteria: [
      'Technical feasibility validated (POC or technical review)',
      'Pricing proposal drafted',
      'Pilot results reviewed (if applicable)',
      'Value proposition refined based on buyer feedback',
    ],
    keySignals: 'Pricing proposals, POC results, fee structures, pilot discussions.',
  },
  {
    number: 4,
    name: 'Proposal',
    duration: '2-6 months',
    objective: 'Build pricing matrix, secure internal approvals, send formal proposal.',
    exitCriteria: [
      'Formal proposal sent and received',
      'Multi-department alignment achieved',
      'Budget discussions initiated or completed',
      'Executive stakeholders briefed',
      'Internal buy-in from key departments',
    ],
    keySignals: 'Multi-department meetings, budget discussions, executive escalations, internal buy-in references.',
  },
  {
    number: 5,
    name: 'Negotiate',
    duration: '4-12 weeks',
    objective: 'Revise pricing/terms, secure written commitment, draft contract.',
    exitCriteria: [
      'Contract terms agreed in principle',
      'SLA expectations documented',
      'Procurement engaged and active',
      'Legal redlines identified and addressed',
      'Written commitment pathway clear',
    ],
    keySignals: 'Contract terms, SLA discussions, redlines, procurement engagement.',
  },
  {
    number: 6,
    name: 'Contract',
    duration: '4-12 weeks',
    objective: 'Finalize redlines, obtain signatures, begin implementation planning. May overlap with Stage 7.',
    exitCriteria: [
      'MSA executed',
      'Legal sign-off obtained',
      'Implementation kickoff scheduled',
      'All commercial terms finalized',
    ],
    keySignals: 'MSA execution, legal sign-off, implementation kickoff discussions.',
  },
  {
    number: 7,
    name: 'Implement',
    duration: '4-12 weeks',
    objective: 'Technical integration, CW checklist, go-live. Closed Won = go-live complete.',
    exitCriteria: [
      'API integration complete',
      'Sandbox testing passed',
      'Data mapping validated',
      'Approval rate tuning completed',
      'Production traffic live',
    ],
    keySignals: 'API setup, sandbox testing, data mapping, approval rate tuning, production traffic.',
  },
];

function StagesSection() {
  return (
    <Section id="stages" title="Deal Stages, Exit Criteria & Objectives" icon={Layers}>
      <p className="text-sm text-muted-foreground">
        SIS infers the deal stage from transcript content alone &mdash; no CRM data is used. Agent 1
        determines stage by analyzing topic dominance across all provided calls. Stages 6 and 7
        (Contract & Implement) can run in parallel at Riskified.
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[14%] whitespace-normal">Stage</TableHead>
                  <TableHead className="w-[9%] whitespace-normal">Dur.</TableHead>
                  <TableHead className="w-[20%] whitespace-normal">Objective</TableHead>
                  <TableHead className="w-[30%] whitespace-normal">Exit Criteria</TableHead>
                  <TableHead className="whitespace-normal">Key Signals</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {STAGES.map((stage) => (
                  <TableRow key={stage.number}>
                    <TableCell className="text-xs font-medium align-top whitespace-normal">
                      <span className="inline-flex items-start gap-1.5">
                        <span className="flex size-5 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold shrink-0 mt-0.5">
                          {stage.number}
                        </span>
                        <span className="break-words">{stage.name}</span>
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground align-top whitespace-normal">{stage.duration}</TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-normal align-top break-words">{stage.objective}</TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-normal align-top">
                      <ul className="list-disc list-inside space-y-0.5">
                        {stage.exitCriteria.map((criterion, i) => (
                          <li key={i} className="break-words">{criterion}</li>
                        ))}
                      </ul>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-normal align-top break-words">{stage.keySignals}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Section 4 — Forecast Categories
// ---------------------------------------------------------------------------

const FORECAST_CATEGORIES = [
  {
    category: 'Commit',
    healthRange: '≥ 75',
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    criteria: [
      'Health score 75 or above',
      'Verbal/pricing agreement secured',
      'Mutual success plan (MSP) exists with high specificity',
      'Economic Buyer directly engaged',
      'Strong buyer-confirmed commitments',
      'Catalyst and consequence of inaction present',
    ],
    litmusTest: 'Deal would close even if the AE left tomorrow.',
  },
  {
    category: 'Realistic',
    healthRange: '55 – 74',
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    criteria: [
      'Health score between 55 and 74',
      'Positive or stable momentum',
      'Deal progressing through stages',
      'Manageable gaps (addressable, not structural)',
      'No high no-decision risk',
    ],
    litmusTest: 'No one would be surprised if this closes.',
  },
  {
    category: 'Upside',
    healthRange: '40 – 54',
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    criteria: [
      'Health score between 40 and 54',
      'Active deal but significant unknowns',
      'Could accelerate with right actions',
      'Missing key elements (champion, EB, or MSP)',
    ],
    litmusTest: 'Long shot — no one would be surprised if we lose this.',
  },
  {
    category: 'At Risk',
    healthRange: '< 40',
    color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    criteria: [
      'Health score below 40, OR any of:',
      'Deal gone dark / no response in 3+ weeks',
      'Champion departed or reorganized',
      'Budget frozen or redirected',
      'Stuck in same stage for 2+ quarters',
      'Competitor emerged in late stage',
      'Integration/legal blocked with no clear path',
      'High no-decision risk with weak/no catalyst',
    ],
    litmusTest: 'This deal needs immediate intervention or should be downgraded.',
  },
];

function ForecastSection() {
  return (
    <Section id="forecast" title="Forecast Categories" icon={Target}>
      <p className="text-sm text-muted-foreground">
        Four forecast categories map to health score ranges with qualitative overrides.
        The no-decision risk override can force a deal to &quot;At Risk&quot; regardless of health score.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {FORECAST_CATEGORIES.map((fc) => (
          <Card key={fc.category}>
            <CardHeader className="pb-2 pt-4 px-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">{fc.category}</CardTitle>
                <Badge className={cn('text-xs', fc.color)}>{fc.healthRange}</Badge>
              </div>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-2">
              <ul className="list-disc list-inside text-sm text-muted-foreground space-y-0.5">
                {fc.criteria.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
              <div className="border-t pt-2 mt-2">
                <p className="text-xs text-muted-foreground italic">&quot;{fc.litmusTest}&quot;</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">No-Decision Risk Override</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 text-sm text-muted-foreground">
          <p>
            If Agent 8 reports <strong>no_decision_risk = High</strong> AND <strong>catalyst_strength</strong> is
            &quot;Cosmetic&quot; or &quot;None Identified&quot;, the forecast is forced to <strong>&quot;At Risk&quot;</strong> regardless
            of health score. This override exists because deals without a forcing function can stall
            indefinitely &mdash; the buyer simply never makes a decision. This is the #1 silent killer
            of enterprise pipelines.
          </p>
        </CardContent>
      </Card>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Section 5 — Active Agents
// ---------------------------------------------------------------------------

const AGENTS = [
  {
    id: 'Agent 1',
    name: 'Stage & Progress',
    model: 'Haiku',
    role: 'Infers deal stage from transcript content without CRM data. Detects stage progression, regression, and stalls.',
    topics: [
      'Topic dominance analysis across all calls',
      'Stage regression detection (e.g. pricing renegotiation in late-stage)',
      'Dual-stage detection (Contract + Implement can run in parallel)',
      'Call arc progression across full conversation history',
      'Data quality flags (poor ASR, short calls, missing speakers)',
    ],
  },
  {
    id: 'Agent 2',
    name: 'Relationship & Power Map',
    model: 'Sonnet',
    role: 'Maps all stakeholders, assesses influence and engagement, identifies the champion, and evaluates multi-threading depth.',
    topics: [
      'Stakeholder identification across all departments (Payments, Fraud, Finance, IT, Legal, Procurement, Executive)',
      'Champion identification requiring advocacy behavior evidence (internal selling, timeline driving, access facilitation)',
      'Multi-threading depth assessment (single-threaded vs. properly multi-threaded)',
      'Stakeholder engagement trajectory (newly active, going quiet, departed)',
      'Buying committee power map and influence assessment',
    ],
  },
  {
    id: 'Agent 3',
    name: 'Commercial & Risk',
    model: 'Sonnet',
    role: 'Assesses the commercial state — pricing, budget, ROI, contract terms, objections, and risk signals.',
    topics: [
      'Pricing model analysis (% of GMV, per-transaction, tiered volume)',
      'Buyer-validated ROI and business case strength',
      'Objection tracking across calls (recurring = red flag)',
      'Budget authority signals and approval pathway',
      'Contract status and legal progression',
    ],
  },
  {
    id: 'Agent 4',
    name: 'Momentum & Engagement',
    model: 'Sonnet',
    role: 'Assesses whether buying energy is increasing, stable, or fading. Focuses on buyer behavior, not seller activity.',
    topics: [
      'Buyer-initiated vs. seller-initiated engagement patterns',
      'Call cadence trends against stage-appropriate norms',
      'Topic progression (implementation questions = forward; basic questions = backward)',
      'Action item completion tracking across calls',
      'Talk-time ratio shifts (increasing seller ratio = declining buyer engagement)',
    ],
  },
  {
    id: 'Agent 5',
    name: 'Technical Validation',
    model: 'Sonnet',
    role: 'Assesses technical feasibility, integration complexity, and whether the buyer\'s technical team is engaged.',
    topics: [
      'Platform/stack identification (Shopify, Magento, SFCC, custom)',
      'Integration complexity assessment (API, data mapping, payment coverage)',
      'Technical stakeholder presence and engagement level',
      'POC/pilot progress tracking (test mode → go-live)',
      'Technical blockers (legacy stacks, custom flows, data quality)',
    ],
  },
  {
    id: 'Agent 6',
    name: 'Economic Buyer',
    model: 'Sonnet',
    role: 'Determines whether someone with budget authority knows about, supports, and is actively engaged in the deal.',
    topics: [
      'EB identification by merchant size (Enterprise: CFO/VP Finance; Mid-market: Controller; Growth: CEO/COO)',
      'Direct vs. secondhand EB engagement (call presence required)',
      'Budget language analysis ("approved" vs. "need to present" vs. "not sure")',
      'EB absence in late-stage deals as critical risk signal',
      'Authority verification through behavior, not job title',
    ],
  },
  {
    id: 'Agent 7',
    name: 'MSP & Next Steps',
    model: 'Sonnet',
    role: 'Determines whether the deal is structurally advancing with concrete, buyer-confirmed next steps.',
    topics: [
      'Next step specificity (High: date + owner + deliverable vs. Low: "let\'s reconnect")',
      'Mutual success plan existence and completeness (milestones, ownership, go-live date)',
      'Action item completion tracking (committed → completed across calls)',
      'Specificity trajectory (escalating = good; declining = bad)',
      'Buyer-initiated vs. seller-proposed next steps',
    ],
  },
  {
    id: 'Agent 8',
    name: 'Competitive Displacement',
    model: 'Sonnet',
    role: 'Determines what the buyer is replacing, attachment to status quo, switch drivers, and no-decision risk.',
    topics: [
      'Incumbent/competitor identification (Forter, Signifyd, in-house, manual review, none)',
      'Displacement barrier assessment (contracts, training, integration effort, transition risk)',
      'Catalyst classification (Existential > Structural > Cosmetic)',
      'No-decision risk evaluation (the #1 silent deal killer)',
      'Consequence of inaction analysis',
    ],
  },
  {
    id: 'Agent 9',
    name: 'Open Discovery / Adversarial Validator',
    model: 'Sonnet',
    role: 'Finds what agents 1-8 missed and challenges the most optimistic findings with counter-evidence.',
    topics: [
      'Novel signal discovery (market/timing, cultural, organizational, opportunity, cross-domain risk)',
      'Adversarial challenge of 1-3 most optimistic findings from upstream agents',
      'Counter-evidence search in transcripts for each challenge',
      'Challenge severity rating (Critical: likely wrong; Moderate: overstated; Minor: nuance missing)',
      'Gap identification — signals that span multiple agent domains',
    ],
  },
  {
    id: 'Agent 10',
    name: 'Synthesis',
    model: 'Opus',
    role: 'Synthesizes all 9 agent outputs into a coherent deal assessment with health score, forecast, and actionable insights.',
    topics: [
      'Contradiction map resolution across all agent findings',
      'Deal memo narrative (situation, stakeholders, risks, momentum, unusual signals)',
      'Weighted health score calculation (10 components, 100 total)',
      'Forecast category determination with qualitative overrides',
      'Confidence interval with key unknowns identification',
    ],
  },
];

function AgentsSection() {
  return (
    <Section id="agents" title="Active Agents & Roles" icon={Users}>
      <p className="text-sm text-muted-foreground">
        SIS runs 10 specialized agents in sequence. Agents 1-8 analyze transcripts independently in parallel.
        Agent 9 reads all 8 outputs for adversarial validation. Agent 10 synthesizes everything into the final assessment.
        All agents include anti-sycophancy rules and measure the <em>buyer</em>, not the seller.
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[20%] whitespace-normal">Agent</TableHead>
                  <TableHead className="w-[8%] whitespace-normal">Model</TableHead>
                  <TableHead className="w-[26%] whitespace-normal">Role</TableHead>
                  <TableHead className="whitespace-normal">Focus Areas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {AGENTS.map((agent) => (
                  <TableRow key={agent.id}>
                    <TableCell className="text-xs font-medium align-top whitespace-normal">
                      <span className="flex flex-col gap-0.5">
                        <Badge variant="outline" className="shrink-0 font-mono text-xs w-fit">{agent.id}</Badge>
                        <span className="break-words">{agent.name}</span>
                      </span>
                    </TableCell>
                    <TableCell className="align-top">
                      <Badge variant="secondary" className="text-xs">{agent.model}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-normal align-top break-words">{agent.role}</TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-normal align-top">
                      <ul className="list-disc list-inside space-y-0.5">
                        {agent.topics.map((topic, i) => (
                          <li key={i} className="break-words">{topic}</li>
                        ))}
                      </ul>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">Processing Architecture</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 text-sm text-muted-foreground space-y-2">
          <div className="font-mono text-xs bg-muted rounded-md p-4 overflow-x-auto whitespace-pre">{`Transcripts
    │
    ├─► Agent 1 (Stage)         ─┐
    ├─► Agent 2 (Relationship)  ─┤
    ├─► Agent 3 (Commercial)    ─┤
    ├─► Agent 4 (Momentum)      ─┤  Parallel
    ├─► Agent 5 (Technical)     ─┤  Analysis
    ├─► Agent 6 (Economic Buyer)─┤
    ├─► Agent 7 (MSP/Next Steps)─┤
    └─► Agent 8 (Competitive)   ─┘
                                  │
                                  ▼
                     Agent 9 (Adversarial Validator)
                                  │
                                  ▼
                     Agent 10 (Synthesis)
                                  │
                                  ▼
                     NEVER Rules Check
                                  │
                                  ▼
                     Final Output`}</div>
        </CardContent>
      </Card>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Section 6 — NEVER Rules (moved to last position)
// ---------------------------------------------------------------------------

const NEVER_RULES = [
  {
    id: 'NEVER_COMMIT_WITHOUT_MSP',
    rule: 'Commit forecast requires MSP + High specificity next steps',
    description: 'A "Commit" forecast must be backed by a mutual success plan with high next-step specificity from Agent 7. Buyer-confirmed milestones with dates and owners are required.',
    agent: 'Agent 7 / Agent 10',
  },
  {
    id: 'NEVER_UNRESOLVED_CONTRADICTIONS',
    rule: 'All contradictions must have resolutions',
    description: 'Agent 10\'s contradiction map entries must each include a resolution field. Unexplained contradictions between agent findings are a quality failure.',
    agent: 'Agent 10',
  },
  {
    id: 'NEVER_INFERRED_PRICING',
    rule: 'Pricing numbers must appear in verbatim evidence',
    description: 'Any dollar amounts mentioned in Agent 3\'s (Commercial) narrative must be traceable to verbatim transcript evidence. No inferred or hallucinated pricing figures.',
    agent: 'Agent 3',
  },
  {
    id: 'EVIDENCE_BASED_CHALLENGES',
    rule: 'Agent 9 challenges must be evidence-based',
    description: 'The Open Discovery / Adversarial Validator produces challenges ONLY when transcript evidence supports them. Manufactured challenges are not permitted — if the deal evidence is genuinely strong, Agent 9 states that clearly.',
    agent: 'Agent 9',
  },
  {
    id: 'NEVER_NO_DECISION_RISK_OVERRIDE',
    rule: 'High no-decision risk blocks Commit and Realistic forecasts',
    description: 'If Agent 8 reports no_decision_risk=High AND catalyst_strength is "Cosmetic" or "None Identified", the forecast must be "At Risk". A deal with health 65 but high no-decision risk is NOT "Realistic" — the buyer may never act.',
    agent: 'Agent 8 / Agent 10',
  },
  {
    id: 'NEVER_COMMIT_WITHOUT_COMPELLING_EVENT',
    rule: 'Commit requires a catalyst + consequence of inaction',
    description: 'A "Commit" forecast is blocked if Agent 8 reports no consequence of inaction AND no catalyst strength. A deal with no pain of inaction and no catalyst is not committable.',
    agent: 'Agent 8 / Agent 10',
  },
  {
    id: 'NEVER_EXPANSION_COMMIT_WITHOUT_RELATIONSHIP',
    rule: 'Expansion Commit requires Strong or Adequate relationship',
    description: 'For expansion deals, a "Commit" forecast requires Agent 0E to confirm the account relationship is "Strong" or "Adequate". You cannot commit an expansion deal with a damaged customer relationship.',
    agent: 'Agent 0E / Agent 10',
  },
];

function NeverRulesSection() {
  return (
    <Section id="never-rules" title="NEVER Rules (Hard Guardrails)" icon={ShieldAlert}>
      <p className="text-sm text-muted-foreground">
        NEVER rules are hard constraints that override any scoring or forecasting logic. They fire
        automatically after synthesis and produce violations that must be addressed. The system will not
        produce output that violates these rules.
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[5%] whitespace-normal">#</TableHead>
                  <TableHead className="w-[28%] whitespace-normal">Rule</TableHead>
                  <TableHead className="w-[16%] whitespace-normal">Applies To</TableHead>
                  <TableHead className="whitespace-normal">Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {NEVER_RULES.map((rule, i) => (
                  <TableRow key={rule.id}>
                    <TableCell className="align-top">
                      <Badge variant="destructive" className="text-xs">{i + 1}</Badge>
                    </TableCell>
                    <TableCell className="text-xs font-medium whitespace-normal align-top break-words">{rule.rule}</TableCell>
                    <TableCell className="text-xs text-muted-foreground align-top whitespace-normal break-words">{rule.agent}</TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-normal align-top break-words">{rule.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">Per-Agent NEVER Rules</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 text-sm text-muted-foreground space-y-2">
          <p>In addition to the system-level NEVER rules above, each agent enforces its own constraints:</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 2 — Relationship</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER call someone a &quot;champion&quot; based solely on friendliness or question-asking. Require ADVOCACY behavior evidence.</li>
                <li>NEVER count someone as &quot;engaged&quot; if they were only mentioned by others. Engagement requires call presence.</li>
                <li>NEVER infer seniority or role without transcript evidence.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 3 — Commercial</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER output a specific pricing number derived from inference rather than explicit transcript statement.</li>
                <li>NEVER speculate about budget authority unless explicitly stated by a speaker.</li>
                <li>NEVER assume an objection is resolved just because the seller addressed it. Look for buyer acknowledgment.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 4 — Momentum</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER count seller-side engagement metrics as buyer momentum signals. Measure the BUYER.</li>
                <li>NEVER treat call frequency alone as a momentum indicator &mdash; quality matters more than quantity.</li>
                <li>NEVER assume &quot;busy&quot; explanations from the buyer indicate maintained interest.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 5 — Technical</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER classify a technical topic as &quot;validated&quot; when it was raised but deferred to follow-up.</li>
                <li>NEVER assume technical feasibility without evidence of technical stakeholder assessment.</li>
                <li>NEVER ignore mentions of existing fraud tools &mdash; they are competitive and integration factors.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 6 — Economic Buyer</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER count secondhand EB mentions as EB engagement. &quot;My CFO likes this&quot; without CFO on a call = EB NOT engaged.</li>
                <li>NEVER assume budget approval from enthusiastic champion language.</li>
                <li>NEVER infer budget authority from job title alone &mdash; verify through behavior and language.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 7 — MSP & Next Steps</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER log a next step as &quot;committed&quot; unless the BUYER explicitly confirmed it. Seller proposing ≠ buyer committing.</li>
                <li>NEVER treat seller&apos;s recap of next steps as buyer confirmation unless the buyer explicitly agreed.</li>
                <li>NEVER assume actions were completed unless confirmed in a subsequent call.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 8 — Competitive</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER name a specific competitor&apos;s pricing or contract details inferred from context.</li>
                <li>NEVER assume the buyer is dissatisfied with their current solution without evidence.</li>
                <li>NEVER underestimate &quot;no decision&quot; risk &mdash; it kills more deals than competitors do.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2">
              <p className="font-medium text-foreground text-xs">Agent 9 — Open Discovery / Adversarial</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER pad findings when nothing new is found. Empty novel_findings is valid output.</li>
                <li>NEVER duplicate what agents 1-8 already captured. Value is additive only.</li>
                <li>ALWAYS produce at least one adversarial challenge. Every deal has findings that deserve scrutiny.</li>
              </ul>
            </div>
            <div className="border rounded-md p-2 sm:col-span-2">
              <p className="font-medium text-foreground text-xs">Agent 10 — Synthesis</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-xs">
                <li>NEVER produce health score &gt;70 if EB has never appeared on calls.</li>
                <li>NEVER produce health score &gt;65 if no champion identified.</li>
                <li>NEVER produce Commit forecast without Level 3+ commitments and MSP.</li>
                <li>NEVER leave contradictions unresolved.</li>
                <li>NEVER ignore Agent 9&apos;s adversarial challenges.</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Confidence Penalties
// ---------------------------------------------------------------------------

const CONFIDENCE_PENALTIES = [
  {
    condition: 'Single transcript',
    penalty: '-15%',
    description: 'When only one transcript is available, the agent has limited evidence to work with. Confidence is reduced by 15 percentage points to reflect this data limitation.',
  },
  {
    condition: 'Contradicting evidence',
    penalty: '-10%',
    description: 'When the agent identifies contradicting signals across transcripts, confidence is reduced by 10 percentage points. Contradictions indicate genuine uncertainty.',
  },
  {
    condition: 'Stale data (>30 days)',
    penalty: '-5%',
    description: 'When the most recent transcript is older than 30 days, confidence is reduced by 5 percentage points. Deal dynamics may have shifted since the last recorded interaction.',
  },
  {
    condition: 'Sparse data ceiling',
    penalty: 'Capped at 75%',
    description: 'When fewer than 3 transcripts are available (sparse_data_flag=true), confidence is hard-capped at 75% regardless of what the AI self-reports. You cannot be highly confident about a deal with minimal evidence.',
  },
];

function ConfidencePenaltiesSection() {
  return (
    <Section id="confidence-penalties" title="Confidence Penalties" icon={Gauge}>
      <p className="text-sm text-muted-foreground">
        After each agent produces its confidence score, the system applies automatic penalties based
        on objective data quality signals. These adjustments prevent over-confidence when the underlying
        data is limited, stale, or contradictory. Penalties stack and are applied before the output flows
        to downstream agents.
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[25%] whitespace-normal">Condition</TableHead>
                  <TableHead className="w-[15%] whitespace-normal">Penalty</TableHead>
                  <TableHead className="whitespace-normal">Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {CONFIDENCE_PENALTIES.map((penalty) => (
                  <TableRow key={penalty.condition}>
                    <TableCell className="text-xs font-medium whitespace-normal align-top break-words">{penalty.condition}</TableCell>
                    <TableCell className="align-top">
                      <Badge variant="secondary" className="text-xs font-mono">{penalty.penalty}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-normal align-top break-words">{penalty.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">How Penalties Stack</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 text-sm text-muted-foreground space-y-2">
          <p>
            Penalties are applied sequentially and stack. For example, a deal with a single transcript
            (older than 30 days) would receive: raw confidence - 15% (single transcript) - 5% (stale data) =
            adjusted confidence. The result is then capped at 0% minimum and 100% maximum.
          </p>
          <p>
            The sparse data ceiling is applied last and overrides the adjusted value if it exceeds 75%.
          </p>
          <p className="font-medium text-foreground text-xs mt-2">
            Example: Agent reports 88% confidence with 1 transcript, 45 days old →
            88% - 15% - 5% = 68% (no sparse ceiling needed since already below 75%)
          </p>
        </CardContent>
      </Card>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

const SECTION_IDS = TOC_ITEMS.map((item) => item.id);

export default function MethodologyPage() {
  const activeId = useScrollSpy(SECTION_IDS);

  return (
    <div id="top" className="p-4 sm:p-6 max-w-full overflow-x-hidden scroll-smooth">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Methodology</h1>
        <p className="text-sm text-muted-foreground">
          How SIS scores deals, forecasts outcomes, and what each agent analyzes.
          This page documents the research, logic, and guardrails behind every assessment.
        </p>
      </div>

      {/* Mobile TOC — sticky bar (visible below xl) */}
      <MobileToc activeId={activeId} />

      <div className="flex gap-8 max-w-full overflow-x-hidden mt-4">
        {/* Main content */}
        <div className="flex-1 min-w-0 overflow-x-hidden space-y-2">
          <ResearchSection />
          <HealthScoreSection />
          <BuyingCultureSection />
          <StagesSection />
          <ForecastSection />
          <AgentsSection />
          <NeverRulesSection />
          <ConfidencePenaltiesSection />
        </div>

        {/* Desktop TOC — sticky right rail (visible at xl+) */}
        <aside className="hidden xl:block w-56 shrink-0">
          <div className="sticky top-6">
            <TableOfContents activeId={activeId} />
          </div>
        </aside>
      </div>
    </div>
  );
}
