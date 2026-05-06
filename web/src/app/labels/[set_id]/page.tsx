import { getDrugStatements } from "@/lib/api";
import { StatementsClient } from "./statements-client";

export default async function DrugStatementsPage({
  params,
}: {
  params: Promise<{ set_id: string }>;
}) {
  const { set_id } = await params;

  try {
    const statements = await getDrugStatements(set_id);
    const drugName = statements.length > 0 ? statements[0].drug_name : "Unknown Drug";
    return <StatementsClient drugName={drugName} statements={statements} />;
  } catch {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center p-8 bg-surface rounded-xl border border-border shadow-sm">
          <p className="text-text-muted font-medium">Drug not found.</p>
        </div>
      </div>
    );
  }
}
