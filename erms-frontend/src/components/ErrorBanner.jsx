/**
 * Shows the normalised API error. A 409 carries `currentStatus`, which tells the
 * user the claim moved under them (duplicate click, another approver was faster).
 */
export default function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;
  const conflict = error.status === 409;
  return (
    <div className={`mb-4 flex items-start gap-3 rounded-md border px-3 py-2 text-sm ${conflict ? "border-butter-300 bg-butter-100" : "border-rose-pastel bg-rose-pastel/40"}`}>
      <div className="flex-1">
        <p>{error.message}</p>
        {conflict && error.currentStatus && (
          <p className="mt-1 text-muted">The claim is now {error.currentStatus.toLowerCase()}. The page has been refreshed.</p>
        )}
      </div>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="text-muted hover:text-ink" aria-label="Dismiss">
          ✕
        </button>
      )}
    </div>
  );
}
