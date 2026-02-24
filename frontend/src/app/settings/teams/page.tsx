'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { usePermissions } from '@/lib/permissions';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Plus, Users, Building2 } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Team {
  id: string;
  name: string;
  level: string;
  parent_id: string | null;
  leader_id: string | null;
}

interface UserRecord {
  id: string;
  name: string;
  email: string;
  role: string;
  team_id: string | null;
}

// ---------------------------------------------------------------------------
// Add Team Dialog
// ---------------------------------------------------------------------------

function AddTeamDialog({
  teams,
  onCreated,
}: {
  teams: Team[];
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [level, setLevel] = useState('team');
  const [parentId, setParentId] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await api.teams.create({
        name: name.trim(),
        level,
        parent_id: parentId || undefined,
      });
      setName('');
      setLevel('team');
      setParentId('');
      setOpen(false);
      onCreated();
    } catch (err) {
      // error handling
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4 mr-1" /> Add Team
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Team</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4 pt-2">
          <Input
            placeholder="Team name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Select value={level} onValueChange={setLevel}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="org">Organization</SelectItem>
              <SelectItem value="division">Division</SelectItem>
              <SelectItem value="team">Team</SelectItem>
            </SelectContent>
          </Select>
          <Select value={parentId} onValueChange={setParentId}>
            <SelectTrigger>
              <SelectValue placeholder="Parent team (optional)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">None (root)</SelectItem>
              {teams.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name} ({t.level})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleSubmit} disabled={submitting || !name.trim()}>
            {submitting ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Add User Dialog
// ---------------------------------------------------------------------------

function AddUserDialog({
  teams,
  onCreated,
}: {
  teams: Team[];
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('ic');
  const [teamId, setTeamId] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!name.trim() || !email.trim()) return;
    setSubmitting(true);
    try {
      await api.users.create({
        name: name.trim(),
        email: email.trim(),
        role,
        team_id: teamId || undefined,
      });
      setName('');
      setEmail('');
      setRole('ic');
      setTeamId('');
      setOpen(false);
      onCreated();
    } catch (err) {
      // error handling
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Plus className="size-4 mr-1" /> Add User
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4 pt-2">
          <Input
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="gm">General Manager</SelectItem>
              <SelectItem value="vp">VP Sales</SelectItem>
              <SelectItem value="team_lead">Team Lead</SelectItem>
              <SelectItem value="ic">IC</SelectItem>
            </SelectContent>
          </Select>
          <Select value={teamId} onValueChange={setTeamId}>
            <SelectTrigger>
              <SelectValue placeholder="Assign to team (optional)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">No team</SelectItem>
              {teams.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !name.trim() || !email.trim()}
          >
            {submitting ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  gm: 'GM',
  vp: 'VP',
  team_lead: 'TL',
  ic: 'IC',
};

const LEVEL_ICONS: Record<string, React.ElementType> = {
  org: Building2,
  division: Building2,
  team: Users,
};

export default function TeamManagementPage() {
  const { isAdmin } = usePermissions();
  const router = useRouter();
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [teamsData, usersData] = await Promise.all([
        api.teams.list(),
        api.users.list(),
      ]);
      setTeams(teamsData);
      setUsers(usersData);
    } catch {
      // If not admin, the API will return 403
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) {
      router.push('/pipeline');
      return;
    }
    loadData();
  }, [isAdmin, router, loadData]);

  if (!isAdmin) return null;

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Team Management</h1>
        <div className="animate-pulse space-y-4">
          <div className="h-32 rounded bg-muted" />
          <div className="h-32 rounded bg-muted" />
        </div>
      </div>
    );
  }

  // Build a team-name lookup for users
  const teamNameMap = new Map(teams.map((t) => [t.id, t.name]));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Team Management</h1>
          <p className="text-sm text-muted-foreground">
            {teams.length} teams, {users.length} active users
          </p>
        </div>
        <div className="flex gap-2">
          <AddTeamDialog teams={teams} onCreated={loadData} />
          <AddUserDialog teams={teams} onCreated={loadData} />
        </div>
      </div>

      {/* Teams Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Teams</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Level</th>
                  <th className="pb-2 pr-4">Parent</th>
                  <th className="pb-2 pr-4">Members</th>
                </tr>
              </thead>
              <tbody>
                {teams.map((team) => {
                  const parentName = team.parent_id
                    ? teamNameMap.get(team.parent_id) || '--'
                    : '--';
                  const memberCount = users.filter(
                    (u) => u.team_id === team.id
                  ).length;
                  const LevelIcon = LEVEL_ICONS[team.level] || Users;

                  return (
                    <tr key={team.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">
                        <div className="flex items-center gap-2">
                          <LevelIcon className="size-4 text-muted-foreground" />
                          {team.name}
                        </div>
                      </td>
                      <td className="py-2 pr-4 capitalize">{team.level}</td>
                      <td className="py-2 pr-4">{parentName}</td>
                      <td className="py-2 pr-4">{memberCount}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Users</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Email</th>
                  <th className="pb-2 pr-4">Role</th>
                  <th className="pb-2 pr-4">Team</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{user.name}</td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {user.email}
                    </td>
                    <td className="py-2 pr-4">
                      <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium">
                        {ROLE_LABELS[user.role] || user.role}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      {user.team_id
                        ? teamNameMap.get(user.team_id) || '--'
                        : '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
