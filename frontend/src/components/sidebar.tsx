'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  LayoutDashboard,
  FileText,
  GitCompare,
  Users,
  TrendingUp,
  Award,
  Upload,
  Play,
  MessageSquare,
  Calendar,
  ThumbsUp,
  Settings,
  Code,
  DollarSign,
  BarChart3,
  ClipboardList,
  CheckCircle,
  Mail,
  Database,
  ChevronDown,
  ChevronRight,
  Menu,
  LogOut,
  User,
} from 'lucide-react';

import { useAuth } from '@/lib/auth';

import { cn } from '@/lib/utils';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Analytics',
    items: [
      { label: 'Pipeline Overview', href: '/pipeline', icon: LayoutDashboard },
      { label: 'Deal Detail', href: '/deals', icon: FileText },
      { label: 'Divergence', href: '/divergence', icon: GitCompare },
      { label: 'Team Rollup', href: '/team-rollup', icon: Users },
      { label: 'Forecast', href: '/forecast', icon: TrendingUp },
      { label: 'Rep Scorecard', href: '/rep-scorecard', icon: Award },
    ],
  },
  {
    label: 'Actions',
    items: [
      { label: 'Upload Transcript', href: '/upload', icon: Upload },
      { label: 'Run Analysis', href: '/analyze', icon: Play },
      { label: 'Chat', href: '/chat', icon: MessageSquare },
      { label: 'Meeting Prep', href: '/meeting-prep', icon: Calendar },
    ],
  },
  {
    label: 'Admin',
    items: [
      { label: 'Feedback', href: '/feedback', icon: ThumbsUp },
      { label: 'Calibration', href: '/calibration', icon: Settings },
      { label: 'Prompt Versions', href: '/prompts', icon: Code },
      { label: 'Costs', href: '/costs', icon: DollarSign },
      { label: 'Usage', href: '/usage', icon: BarChart3 },
      { label: 'Activity Log', href: '/activity-log', icon: ClipboardList },
      { label: 'Golden Tests', href: '/golden-tests', icon: CheckCircle },
      { label: 'Digest', href: '/digest', icon: Mail },
      { label: 'Seeding', href: '/seeding', icon: Database },
    ],
  },
];

function NavLink({ item, onClick }: { item: NavItem; onClick?: () => void }) {
  const pathname = usePathname();
  const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={cn(
        'flex min-h-[44px] items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
        isActive
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground'
      )}
    >
      <Icon className="size-4 shrink-0" />
      <span>{item.label}</span>
    </Link>
  );
}

function NavGroupSection({
  group,
  onItemClick,
}: {
  group: NavGroup;
  onItemClick?: () => void;
}) {
  const [open, setOpen] = useState(true);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger
        className={cn(
          'flex min-h-[44px] w-full items-center justify-between px-3 py-2',
          'text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/60',
          'hover:text-sidebar-foreground/80 transition-colors'
        )}
      >
        <span>{group.label}</span>
        {open ? (
          <ChevronDown className="size-3.5" />
        ) : (
          <ChevronRight className="size-3.5" />
        )}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <nav className="flex flex-col gap-0.5 pb-2">
          {group.items.map((item) => (
            <NavLink key={item.href} item={item} onClick={onItemClick} />
          ))}
        </nav>
      </CollapsibleContent>
    </Collapsible>
  );
}

function SidebarLogo() {
  return (
    <div className="flex items-center gap-3 px-3 py-4 border-b border-sidebar-border">
      <div className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold text-sm shrink-0">
        S
      </div>
      <div className="flex flex-col">
        <span className="text-sm font-bold text-sidebar-foreground leading-tight">
          SIS
        </span>
        <span className="text-xs text-sidebar-foreground/60 leading-tight">
          Sales Intelligence
        </span>
      </div>
    </div>
  );
}

function SidebarUserFooter() {
  const { user, logout } = useAuth();

  if (!user) return null;

  const roleLabel =
    user.role === 'admin'
      ? 'Admin'
      : user.role === 'team_lead'
        ? 'Team Lead'
        : 'IC';

  return (
    <div className="border-t border-sidebar-border px-3 py-3">
      <div className="flex items-center gap-3">
        <div className="flex size-8 items-center justify-center rounded-full bg-sidebar-accent text-sidebar-accent-foreground shrink-0">
          <User className="size-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-sidebar-foreground truncate">
            {user.username}
          </p>
          <p className="text-xs text-sidebar-foreground/60">{roleLabel}</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={logout}
          className="size-8 shrink-0 text-sidebar-foreground/60 hover:text-sidebar-foreground"
          aria-label="Sign out"
        >
          <LogOut className="size-4" />
        </Button>
      </div>
    </div>
  );
}

function SidebarInner({ onItemClick }: { onItemClick?: () => void }) {
  return (
    <div className="flex h-full flex-col bg-sidebar">
      <SidebarLogo />
      <div className="flex-1 overflow-y-auto py-2">
        <div className="flex flex-col gap-1 px-2">
          {NAV_GROUPS.map((group) => (
            <NavGroupSection
              key={group.label}
              group={group}
              onItemClick={onItemClick}
            />
          ))}
        </div>
      </div>
      <SidebarUserFooter />
    </div>
  );
}

/** Desktop fixed sidebar — hidden on mobile */
export function DesktopSidebar() {
  return (
    <aside className="hidden lg:flex lg:fixed lg:inset-y-0 lg:left-0 lg:w-64 lg:flex-col lg:border-r lg:border-sidebar-border">
      <SidebarInner />
    </aside>
  );
}

/** Mobile hamburger button + Sheet drawer */
export function MobileSidebar() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden fixed top-3 left-3 z-40 size-11"
          aria-label="Open navigation menu"
        >
          <Menu className="size-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 p-0" showCloseButton={false}>
        <SheetHeader className="sr-only">
          <SheetTitle>Navigation</SheetTitle>
        </SheetHeader>
        <SidebarInner onItemClick={() => setOpen(false)} />
      </SheetContent>
    </Sheet>
  );
}
