export type User = { id: number; name: string; email: string; role: "admin" | "operador" | "motorista"; active?: boolean };
export type Producer = { id: number; name: string; phone?: string; province: string; district?: string };
export type Product = { id: number; name: string; category?: string; unit: string };
export type Lot = {
  id: number; code: string; quantity: number; harvest_date: string; origin?: string; status: string;
  producer: Producer; product: Product;
};
export type DeliveryEvent = { status: string; note?: string; created_at: string };
export type Delivery = {
  id: number; code: string; destination: string; status: string; receiver_name?: string;
  created_at: string; lot: Lot; driver?: User; events: DeliveryEvent[];
};
export type Page<T> = { items: T[]; total: number };
export type Stats = {
  producers: number; lots: number; lots_available: number; deliveries_active: number;
  deliveries_done: number; total_kg: number;
  by_product: { name: string; kg: number }[]; by_status: { status: string; count: number }[];
};
export type Trace = {
  code: string; product: string; quantity: number; unit: string; harvest_date: string; origin?: string;
  status: string; producer: { name: string; province: string; district?: string };
  timeline: { status: string; note?: string; at: string }[];
};

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "") || "/api";

let token: string | null = localStorage.getItem("token");
export const setToken = (t: string | null) => {
  token = t;
  t ? localStorage.setItem("token", t) : localStorage.removeItem("token");
};
export const hasToken = () => !!token;

export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && token) { setToken(null); location.reload(); }
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    const d = e.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x: any) => x.msg).join("; ") : "Erro no pedido");
  }
  return res.json();
}
