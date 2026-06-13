export interface ProductPrice {
  amount: number | null;
  currency: string;
}

export interface Product {
  id: string;
  name: string;
  summary?: string;
  price: ProductPrice;
  in_stock: boolean;
  image_url?: string | null;
  url?: string;
}

export interface CartItem {
  product_id: string;
  quantity: number;
  perishable_flag?: boolean;
  price: number;
  name: string;
  image_url?: string | null;
}

export interface DeliveryInfo {
  city?: string;
  date?: string;
  validated?: string;
  delivery_rate?: string;
}

export interface CheckoutInfo {
  recipient?: { name?: string; phone?: string; address?: string };
  sender?: { name?: string };
  gift_message?: string;
}

export type UiActionType = "show_products" | "update_cart" | "show_checkout" | null;

export interface SessionPayload {
  products?: Product[];
  selected_product?: Product;
  search_query?: string;
  cart?: CartItem[];
  delivery_info?: DeliveryInfo;
  checkout_info?: CheckoutInfo;
  error?: string;
}

export interface ShowProductsPayload extends SessionPayload {
  products?: Product[];
}

export interface UpdateCartPayload extends SessionPayload {
  cart: CartItem[];
}

export interface CheckoutPayload extends SessionPayload {
  checkout_url?: string;
  order_ref?: string;
  summary?: {
    grand_total?: number;
    currency?: string;
    items_total?: number;
    delivery_fee?: number;
    addons_total?: number;
  };
  expires_at?: string;
}

export type UiPayload = ShowProductsPayload | UpdateCartPayload | CheckoutPayload;

export interface UiEnvelope {
  type: "ui";
  action: Exclude<UiActionType, null>;
  payload: UiPayload;
}

export interface AudioEnvelope {
  type: "audio";
  data: string;
}

export type ControlAction = "mic_pause" | "mic_resume" | "processing" | "error";

export interface ControlEnvelope {
  type: "control";
  action: ControlAction;
  message?: string;
}

export type ServerEnvelope = UiEnvelope | AudioEnvelope | ControlEnvelope;

export interface UiState {
  action: UiActionType;
  payload: UiPayload | null;
}

export interface SessionSnapshot {
  cart: CartItem[];
  delivery_info: DeliveryInfo;
  checkout_info: CheckoutInfo;
  products: Product[];
  search_query?: string;
  selected_product?: Product;
}

export type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

export type VoicePhase = "idle" | "listening" | "speaking" | "processing";

export type OrderStep = "discover" | "cart" | "delivery" | "checkout";
