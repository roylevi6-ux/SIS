'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { PipelineFlowTab } from '@/components/trends/pipeline-flow-tab';
import { ForecastMovementTab } from '@/components/trends/forecast-movement-tab';
import { DealHealthTab } from '@/components/trends/deal-health-tab';
import { VelocityTab } from '@/components/trends/velocity-tab';
import { TeamComparisonTab } from '@/components/trends/team-comparison-tab';

const WEEK_OPTIONS = [4, 8, 12] as const;

export default function TrendsPage() {
  const [weeks, setWeeks] = useState<number>(4);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Deal Trends</h1>
          <p className="text-muted-foreground text-sm">Pipeline analytics over time</p>
        </div>
        <div className="flex gap-1">
          {WEEK_OPTIONS.map((w) => (
            <Badge
              key={w}
              variant={weeks === w ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setWeeks(w)}
            >
              {w}w
            </Badge>
          ))}
        </div>
      </div>

      <Tabs defaultValue="pipeline-flow">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="pipeline-flow">Pipeline Flow</TabsTrigger>
          <TabsTrigger value="forecast-movement">Forecast Movement</TabsTrigger>
          <TabsTrigger value="deal-health">Deal Health</TabsTrigger>
          <TabsTrigger value="velocity">Velocity</TabsTrigger>
          <TabsTrigger value="team-comparison">Team Comparison</TabsTrigger>
        </TabsList>
        <TabsContent value="pipeline-flow">
          <PipelineFlowTab weeks={weeks} />
        </TabsContent>
        <TabsContent value="forecast-movement">
          <ForecastMovementTab weeks={weeks} />
        </TabsContent>
        <TabsContent value="deal-health">
          <DealHealthTab weeks={weeks} />
        </TabsContent>
        <TabsContent value="velocity">
          <VelocityTab weeks={weeks} />
        </TabsContent>
        <TabsContent value="team-comparison">
          <TeamComparisonTab weeks={weeks} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
