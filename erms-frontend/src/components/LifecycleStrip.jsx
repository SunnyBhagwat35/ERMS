/**
 * Draft → Submitted → Approved → Paid, with the current step highlighted.
 * A rejected claim shows "Rejected" in place of "Approved".
 */
export default function LifecycleStrip({ status }) {
  const steps = ["DRAFT", "SUBMITTED", status === "REJECTED" ? "REJECTED" : "APPROVED", "PAID"];
  const order = { DRAFT: 0, SUBMITTED: 1, APPROVED: 2, REJECTED: 2, PAID: 3 };
  const current = order[status] ?? 0;
  const labels = { DRAFT: "Draft", SUBMITTED: "Submitted", APPROVED: "Approved", REJECTED: "Rejected", PAID: "Paid" };

  return (
    <ol className="flex items-center gap-2 text-sm">
      {steps.map((step, index) => {
        const done = index < current;
        const active = index === current;
        const tone = active
          ? step === "REJECTED"
            ? "bg-rose-pastel text-ink"
            : "bg-mint-300 text-ink"
          : done
            ? "bg-mint-100 text-mint-700"
            : "bg-slate-pastel text-muted";
        return (
          <li key={step} className="flex items-center gap-2">
            <span className={`rounded-full px-3 py-1 ${tone} ${active ? "font-semibold" : ""}`}>{labels[step]}</span>
            {index < steps.length - 1 && <span className="h-px w-6 bg-line" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}
