import { ReviewClient } from "./review-client";
import { getReview } from "@/lib/api";

export default async function ReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  try {
    const data = await getReview(id);
    return <ReviewClient initialData={data} />;
  } catch {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center p-8 bg-surface rounded-xl border border-border shadow-sm">
          <p className="text-text-muted font-medium">Review not found.</p>
        </div>
      </div>
    );
  }
}
