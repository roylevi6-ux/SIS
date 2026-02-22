import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Database } from 'lucide-react';

export default function SeedingPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Retrospective Seeding</h1>
        <p className="text-sm text-muted-foreground">Coming Soon</p>
      </div>
      <Card className="max-w-lg">
        <CardHeader className="pb-2 pt-6 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
              <Database className="h-5 w-5 text-muted-foreground" />
            </div>
            <CardTitle className="text-base">Retrospective Seeding — Coming Soon</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-6 pb-6">
          <p className="text-sm text-muted-foreground leading-relaxed">
            Seed historical deal data for testing and calibration. This feature will let you import
            closed-won and closed-lost deal transcripts to build a labeled dataset for evaluating
            pipeline accuracy and calibrating scoring thresholds.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
