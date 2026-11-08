const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 });

// The API sends decimals as strings ("5000.00"); format for display only, never do maths on floats.
export function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isNaN(n) ? String(value) : inr.format(n);
}

export function dateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function date(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { dateStyle: "medium" });
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export const STATUS_LABEL = {
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  PAID: "Paid",
};
