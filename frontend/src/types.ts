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

export interface KaprukaCategory {
  name: string;
  label?: string;
  emoji?: string;
  iconUrl?: string;
  url?: string;
  children?: KaprukaCategory[];
}

export type UiActionType =
  | "show_products"
  | "show_categories"
  | "update_cart"
  | "show_checkout"
  | null;

export type OrderPhase = "shopping" | "link_ready" | "branch_pending";

export interface CheckoutCartSnapshot {
  item_count: number;
  product_ids: string[];
  lines?: Array<{ product_id: string; quantity: number }>;
}

export interface SessionPayload {
  products?: Product[];
  selected_product?: Product;
  search_query?: string;
  cart?: CartItem[];
  delivery_info?: DeliveryInfo;
  checkout_info?: CheckoutInfo;
  categories?: KaprukaCategory[];
  category?: string;
  subcategory?: string;
  error?: string;
  order_phase?: OrderPhase;
  checkout_stale?: boolean;
  checkout_cart_snapshot?: CheckoutCartSnapshot;
}

export interface ShowProductsPayload extends SessionPayload {
  products?: Product[];
}

export interface ShowCategoriesPayload extends SessionPayload {
  categories?: KaprukaCategory[];
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

export type UiPayload =
  | ShowProductsPayload
  | ShowCategoriesPayload
  | UpdateCartPayload
  | CheckoutPayload;

export interface UiEnvelope {
  type: "ui";
  action: Exclude<UiActionType, null>;
  payload: UiPayload;
}

export interface AudioEnvelope {
  type: "audio";
  data: string;
}

export type ControlAction =
  | "mic_pause"
  | "mic_resume"
  | "processing"
  | "error"
  | "session_ready"
  | "live_ready"
  | "live_error";

export interface ControlEnvelope {
  type: "control";
  action: ControlAction;
  message?: string;
}

export type ChatRole = "user" | "assistant";

export type ChatMessageKind =
  | "text"
  | "products"
  | "categories"
  | "checkout"
  | "delivery"
  | "cart_notice"
  | "branch_prompt";

export type ChatMessageStatus = "streaming" | "final";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  kind: ChatMessageKind;
  content?: string;
  status?: ChatMessageStatus;
  products?: Product[];
  categories?: KaprukaCategory[];
  searchQuery?: string;
  searchError?: string;
  checkoutPayload?: CheckoutPayload;
  delivery?: DeliveryInfo;
  cartItemName?: string;
}

export interface TextEnvelope {
  type: "text";
  role: ChatRole;
  content: string;
}

export interface TranscriptEnvelope {
  type: "transcript";
  role: ChatRole;
  content: string;
  final?: boolean;
}

export type ServerEnvelope =
  | UiEnvelope
  | AudioEnvelope
  | ControlEnvelope
  | TextEnvelope
  | TranscriptEnvelope;

export interface UiState {
  action: UiActionType;
  payload: UiPayload | null;
}

export interface SessionSnapshot {
  cart: CartItem[];
  delivery_info: DeliveryInfo;
  checkout_info: CheckoutInfo;
  products: Product[];
  categories: KaprukaCategory[];
  search_query?: string;
  selected_product?: Product;
  order_phase?: OrderPhase;
  checkout_stale?: boolean;
  checkout_cart_snapshot?: CheckoutCartSnapshot;
  checkout_url?: string;
}

export type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

export type VoicePhase = "idle" | "listening" | "speaking" | "processing";

export type OrderStep = "discover" | "cart" | "delivery" | "checkout";
