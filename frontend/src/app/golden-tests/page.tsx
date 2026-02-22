import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FlaskConical } from 'lucide-react';

export default function GoldenTestsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Golden Tests</h1>
        <p className="text-sm text-muted-foreground">Coming Soon</p>
      </div>
      <Card className="max-w-lg">
        <CardHeader className="pb-2 pt-6 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
              <FlaskConical className="h-5 w-5 text-muted-foreground" />
            </div>
            <CardTitle className="text-base">Golden Tests — Coming Soon</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-6 pb-6">
          <p className="text-sm text-muted-foreground leading-relaxed">
            Compare current pipeline outputs against golden test baselines. This feature will allow
            you to run the full 10-agent pipeline against a curated set of reference deals and
            measure scoring accuracy and consistency across versions.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
