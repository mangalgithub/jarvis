export function money(amount = 0) {
  return `Rs ${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function shortDate(value?: string) {
  if (!value) return "Today";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function timeAgo(date?: string) {
  if (!date) return "";
  try {
    const now = new Date();
    const then = new Date(date);
    const diff = now.getTime() - then.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return shortDate(date);
  } catch {
    return "";
  }
}
