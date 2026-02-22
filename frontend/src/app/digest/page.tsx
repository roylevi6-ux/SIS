import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Mail } from 'lucide-react';

export default function DigestPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Daily Digest</h1>
        <p className="text-sm text-muted-foreground">Coming Soon</p>
      </div>
      <Card className="max-w-lg">
        <CardHeader className="pb-2 pt-6 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
              <Mail className="h-5 w-5 text-muted-foreground" />
            </div>
            <CardTitle className="text-base">Daily Digest — Coming Soon</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-6 pb-6">
          <p className="text-sm text-muted-foreground leading-relaxed">
            Configure automated daily pipeline summary emails. This feature will deliver a concise
            briefing of portfolio health changes, new divergence alerts, and AI-generated action
            items directly to your inbox each morning.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
