export default function DealBriefPage({ params }: { params: { id: string } }) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Deal Brief — {params.id}</h1>
      <p className="text-muted-foreground">Coming soon</p>
    </div>
  );
}
