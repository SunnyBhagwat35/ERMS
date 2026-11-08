import { STATUS_LABEL } from "../utils/format";

const COLOR = {
  DRAFT: "bg-slate-pastel",
  SUBMITTED: "bg-sky-pastel",
  APPROVED: "bg-mint-300",
  REJECTED: "bg-rose-pastel",
  PAID: "bg-lilac-pastel",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${COLOR[status] ?? "bg-slate-pastel"}`}>
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}
