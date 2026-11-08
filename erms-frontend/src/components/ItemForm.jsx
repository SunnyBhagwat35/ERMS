import { useEffect, useState } from "react";
import { today } from "../utils/format";

const empty = (categories) => ({
  category: categories[0]?.id ?? "",
  description: "",
  expense_date: today(),
  amount: "",
});

/**
 * Add or edit one expense item. Pass `initial` to edit; omit it to add.
 * Submits JSON normally, or FormData when a receipt file is chosen.
 */
export default function ItemForm({ categories, initial = null, onSubmit, onCancel, busy }) {
  const [form, setForm] = useState(empty(categories));
  const [file, setFile] = useState(null);

  // Reset the fields whenever we switch between "add" and "edit this item".
  useEffect(() => {
    setForm(
      initial
        ? { category: initial.category, description: initial.description, expense_date: initial.expense_date, amount: initial.amount }
        : empty(categories)
    );
    setFile(null);
  }, [initial, categories]);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  const selected = categories.find((c) => String(c.id) === String(form.category));

  const handleSubmit = async (e) => {
    e.preventDefault();
    let body = form;
    if (file) {
      body = new FormData();
      Object.entries(form).forEach(([key, value]) => body.append(key, value));
      body.append("receipt", file);
    }
    const ok = await onSubmit(body);
    if (ok && !initial) {
      setForm(empty(categories));
      setFile(null);
      e.target.reset(); // clears the file input
    }
  };

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-3 md:grid-cols-6">
      <div className="md:col-span-2">
        <label className="label" htmlFor="category">Category</label>
        <select id="category" name="category" value={form.category} onChange={onChange} className="input" required>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {selected?.max_amount && <p className="mt-1 text-xs text-muted">Limit ₹{selected.max_amount} per item</p>}
      </div>
      <div className="md:col-span-2">
        <label className="label" htmlFor="description">Description</label>
        <input id="description" name="description" value={form.description} onChange={onChange} className="input" required maxLength={255} />
      </div>
      <div>
        <label className="label" htmlFor="expense_date">Date</label>
        <input id="expense_date" type="date" name="expense_date" value={form.expense_date} onChange={onChange} className="input" required max={today()} />
      </div>
      <div>
        <label className="label" htmlFor="amount">Amount (₹)</label>
        <input id="amount" type="number" name="amount" value={form.amount} onChange={onChange} className="input" required min="0.01" step="0.01" />
      </div>
      <div className="md:col-span-4">
        <label className="label" htmlFor="receipt">Receipt (pdf/jpg/png, optional)</label>
        <input id="receipt" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setFile(e.target.files[0] ?? null)} className="text-sm text-muted" />
      </div>
      <div className="flex items-end gap-2 md:col-span-2 md:justify-end">
        {initial && (
          <button type="button" onClick={onCancel} className="btn btn-secondary" disabled={busy}>
            Cancel
          </button>
        )}
        <button type="submit" className="btn btn-primary" disabled={busy || !categories.length}>
          {initial ? "Save item" : "Add item"}
        </button>
      </div>
    </form>
  );
}
