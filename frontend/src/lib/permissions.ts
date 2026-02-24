import { useAuth } from './auth';

type Role = 'admin' | 'gm' | 'vp' | 'team_lead' | 'ic';

const ROLE_RANK: Record<Role, number> = {
  ic: 0,
  team_lead: 1,
  vp: 2,
  gm: 3,
  admin: 4,
};

export function usePermissions() {
  const { user } = useAuth();
  const role = (user?.role ?? 'ic') as Role;

  return {
    role,
    isAdmin: role === 'admin',
    isGmOrAbove: ROLE_RANK[role] >= ROLE_RANK.gm,
    isVpOrAbove: ROLE_RANK[role] >= ROLE_RANK.vp,
    isTlOrAbove: ROLE_RANK[role] >= ROLE_RANK.team_lead,
    canManageTeams: role === 'admin',
    canSeeAllDeals: role === 'admin' || role === 'gm',
    canSeeRollup: ROLE_RANK[role] >= ROLE_RANK.vp,
  };
}
