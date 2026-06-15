export type Language = "en" | "si";

export const LANGUAGES: Language[] = ["en", "si"];

export const LANGUAGE_LABELS: Record<Language, string> = {
  en: "EN",
  si: "සිං",
};

export type StringKey =
  | "header.tagline"
  | "header.title"
  | "header.cart"
  | "header.end"
  | "welcome.connectedTitle"
  | "welcome.connectedSubtitle"
  | "welcome.disconnectedTitle"
  | "welcome.disconnectedSubtitle"
  | "welcome.cta"
  | "welcome.connecting"
  | "input.connected"
  | "input.disconnected"
  | "input.send"
  | "chat.searching"
  | "cart.title"
  | "cart.close"
  | "cart.empty"
  | "cart.items"
  | "cart.delivery"
  | "cart.total"
  | "cart.remove";

const STRINGS: Record<Language, Record<StringKey, string>> = {
  en: {
    "header.tagline": "Kapruka",
    "header.title": "Kapru · Gift Assistant",
    "header.cart": "Cart",
    "header.end": "End",
    "welcome.connectedTitle": "Hi, I'm Kapru",
    "welcome.connectedSubtitle":
      "Your gift concierge for cakes, flowers, and hampers across Sri Lanka. Tap a suggestion below to start.",
    "welcome.disconnectedTitle": "Welcome to Kapruka",
    "welcome.disconnectedSubtitle":
      "Start a chat to browse gifts with your AI concierge — in English, Sinhala, Tamil, or Tanglish.",
    "welcome.cta": "Start chatting with Kapru",
    "welcome.connecting": "Connecting…",
    "input.connected": "Message Kapru…",
    "input.disconnected": "Start chat to type",
    "input.send": "Send",
    "chat.searching": "Kapru is searching Kapruka…",
    "cart.title": "Gift cart",
    "cart.close": "Close",
    "cart.empty": "Your cart is empty. Browse Kapruka picks and tap one to add it.",
    "cart.items": "Items",
    "cart.delivery": "Delivery to",
    "cart.total": "Estimated total",
    "cart.remove": "Remove",
  },
  si: {
    "header.tagline": "කප්රුක",
    "header.title": "කප්රු · තෑගි සහයක",
    "header.cart": "කරත්තය",
    "header.end": "අවසන්",
    "welcome.connectedTitle": "ආයුබෝවන්, මම කප්රු",
    "welcome.connectedSubtitle":
      "ශ්‍රී ලංකාව පුරා කේක්, මල් සහ තෑගි සඳහා ඔබේ සහයකයා. ආරම්භ කිරීමට පහත යෝජනාවක් තට්ටු කරන්න.",
    "welcome.disconnectedTitle": "කප්රුක වෙත සාදරයෙන් පිළිගනිමු",
    "welcome.disconnectedSubtitle":
      "ඉංග්‍රීසි, සිංහල, දෙමළ හෝ ටෑන්ග්ලිෂ් වලින් තෑගි සොයන්න — කතාබහක් ආරම්භ කරන්න.",
    "welcome.cta": "කප්රු සමඟ කතා කරන්න",
    "welcome.connecting": "සම්බන්ධ වෙමින්…",
    "input.connected": "කප්රුට පණිවිඩයක්…",
    "input.disconnected": "ටයිප් කිරීමට කතාබහ ආරම්භ කරන්න",
    "input.send": "යවන්න",
    "chat.searching": "කප්රු කප්රුක සොයමින්…",
    "cart.title": "තෑගි කරත්තය",
    "cart.close": "වසන්න",
    "cart.empty": "ඔබේ කරත්තය හිස්. කප්රුක තෑගි බලා එකක් තට්ටු කර එක් කරන්න.",
    "cart.items": "භාණ්ඩ",
    "cart.delivery": "බෙදාහැරීම",
    "cart.total": "ඇස්තමේන්තුගත එකතුව",
    "cart.remove": "ඉවත් කරන්න",
  },
};

export type Translator = (key: StringKey) => string;

export function getTranslator(language: Language): Translator {
  return (key: StringKey) => STRINGS[language][key] ?? STRINGS.en[key] ?? key;
}
