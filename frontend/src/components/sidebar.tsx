'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  LayoutDashboard,
  Users,
  Award,
  Upload,
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
  BookOpen,
  TrendingUp,
  ChevronDown,
  ChevronRight,
  Menu,
  LogOut,
  User,
} from 'lucide-react';

import { useAuth } from '@/lib/auth';
import { usePermissions } from '@/lib/permissions';

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

type Role = 'ic' | 'team_lead' | 'vp' | 'gm' | 'admin';

const ROLE_RANK: Record<Role, number> = {
  ic: 0,
  team_lead: 1,
  vp: 2,
  gm: 3,
  admin: 4,
};

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  minRole?: Role;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Analytics',
    items: [
      { label: 'Pipeline', href: '/pipeline', icon: LayoutDashboard },
      { label: 'Deal Trends', href: '/trends', icon: TrendingUp },
      { label: 'Team Rollup', href: '/team-rollup', icon: Users, minRole: 'vp' },
      { label: 'Rep Scorecard', href: '/rep-scorecard', icon: Award, minRole: 'team_lead' },
      { label: 'Methodology', href: '/methodology', icon: BookOpen },
    ],
  },
  {
    label: 'Actions',
    items: [
      { label: 'Import & Analyze', href: '/upload', icon: Upload },
      { label: 'Chat', href: '/chat', icon: MessageSquare },
      { label: 'Meeting Prep', href: '/meeting-prep', icon: Calendar },
    ],
  },
  {
    label: 'Admin',
    items: [
      { label: 'Team Management', href: '/settings/teams', icon: Users, minRole: 'admin' },
      { label: 'Display Settings', href: '/settings/display', icon: Settings },
      { label: 'Feedback', href: '/feedback', icon: ThumbsUp, minRole: 'team_lead' },
      { label: 'Calibration', href: '/calibration', icon: Settings, minRole: 'admin' },
      { label: 'Prompt Versions', href: '/prompts', icon: Code, minRole: 'admin' },
      { label: 'Costs', href: '/costs', icon: DollarSign, minRole: 'admin' },
      { label: 'Usage', href: '/usage', icon: BarChart3, minRole: 'admin' },
      { label: 'Activity Log', href: '/activity-log', icon: ClipboardList, minRole: 'admin' },
      { label: 'Golden Tests', href: '/golden-tests', icon: CheckCircle, minRole: 'admin' },
      { label: 'Digest', href: '/digest', icon: Mail, minRole: 'team_lead' },
      { label: 'Seeding', href: '/seeding', icon: Database, minRole: 'admin' },
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
          ? 'bg-sidebar-accent text-sidebar-accent-foreground shadow-[inset_0_0_0_1px_rgba(16,185,129,0.15)]'
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
  const { role } = usePermissions();

  // Filter items by minimum role
  const visibleItems = group.items.filter((item) => {
    if (!item.minRole) return true;
    return ROLE_RANK[role as Role] >= ROLE_RANK[item.minRole];
  });

  // Hide the entire group if no items are visible
  if (visibleItems.length === 0) return null;

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
          {visibleItems.map((item) => (
            <NavLink key={item.href} item={item} onClick={onItemClick} />
          ))}
        </nav>
      </CollapsibleContent>
    </Collapsible>
  );
}

function SidebarLogo() {
  return (
    <div className="flex items-center gap-3 px-4 py-5 border-b border-sidebar-border">
      <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-white font-bold text-sm tracking-tight shadow-lg shadow-brand-500/25 shrink-0" style={{ boxShadow: '0 0 20px rgba(16, 185, 129, 0.2)' }}>
        SIS
      </div>
      <div className="flex flex-col">
        <span className="text-sm font-semibold text-sidebar-foreground leading-tight">
          SIS
        </span>
        <span className="text-[11px] text-sidebar-muted leading-tight">
          Sales Intelligence
        </span>
      </div>
    </div>
  );
}

function SidebarUserFooter() {
  const { user, logout } = useAuth();

  if (!user) return null;

  const roleLabels: Record<string, string> = {
    admin: 'Admin',
    gm: 'General Manager',
    vp: 'VP Sales',
    team_lead: 'Team Lead',
    ic: 'IC',
  };
  const roleLabel = roleLabels[user.role] || user.role;

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

/** Desktop fixed sidebar -- hidden on mobile */
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
