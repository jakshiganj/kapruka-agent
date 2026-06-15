import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import type { CheckoutFormData, CheckoutFormPayload } from "../types";

interface CheckoutFormProps {
  payload: CheckoutFormPayload;
  onSubmit: (data: CheckoutFormData) => void;
  submitting?: boolean;
}

const MIN_ADDRESS_LEN = 3;

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-[#494550]">
        {label}
        {required ? <span className="text-[#ba1a1a]"> *</span> : null}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-lg border border-[#402970]/12 bg-[#F0EEFA]/40 px-3 py-2 text-sm text-[#222222] placeholder:text-[#494550]/50 focus:border-[#402970]/30 focus:bg-white focus:outline-none"
      />
    </label>
  );
}

export function CheckoutForm({ payload, onSubmit, submitting = false }: CheckoutFormProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [sender, setSender] = useState("");
  const [message, setMessage] = useState("");
  const [city, setCity] = useState("");
  const [date, setDate] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!submitting) {
      setPending(false);
    }
  }, [submitting]);

  // Hydrate from backend-extracted details without clobbering user edits:
  // only fill fields the user hasn't typed into yet.
  const edited = useRef<Set<string>>(new Set());
  useEffect(() => {
    const info = payload.checkout_info ?? {};
    const delivery = payload.delivery_info ?? {};
    const recipient = info.recipient ?? {};
    const fill = (key: string, current: string, next: string | undefined, set: (v: string) => void) => {
      if (!edited.current.has(key) && !current && next) {
        set(next);
      }
    };
    fill("name", name, recipient.name, setName);
    fill("phone", phone, recipient.phone, setPhone);
    fill("address", address, recipient.address, setAddress);
    fill("sender", sender, info.sender?.name, setSender);
    fill("message", message, info.gift_message, setMessage);
    fill("city", city, delivery.city, setCity);
    fill("date", date, delivery.date, setDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payload]);

  const mark = (key: string, set: (v: string) => void) => (v: string) => {
    edited.current.add(key);
    set(v);
  };

  const ready =
    name.trim().length > 0 &&
    phone.trim().length > 0 &&
    address.trim().length >= MIN_ADDRESS_LEN &&
    sender.trim().length > 0 &&
    city.trim().length > 0 &&
    date.trim().length > 0;

  const handleSubmit = () => {
    if (!ready || pending) return;
    setPending(true);
    onSubmit({
      recipient: { name: name.trim(), phone: phone.trim(), address: address.trim() },
      sender: { name: sender.trim() },
      gift_message: message.trim() || undefined,
      city: city.trim(),
      date: date.trim(),
    });
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="w-full overflow-hidden rounded-2xl rounded-bl-sm border border-[#402970]/15 bg-white shadow-[0_4px_16px_rgba(64,41,112,0.1)]"
    >
      <div className="border-b border-[#402970]/10 bg-[#F0EEFA] px-5 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-[#402970]">
          Confirm your order
        </p>
        <h2 className="mt-0.5 text-lg font-bold text-[#222222]">Checkout details</h2>
      </div>

      <div className="space-y-3 p-5">
        <Field label="Recipient name" value={name} onChange={mark("name", setName)} required placeholder="Who's it for?" />
        <Field label="Recipient phone" value={phone} onChange={mark("phone", setPhone)} required placeholder="07X XXX XXXX" />
        <Field label="Delivery address" value={address} onChange={mark("address", setAddress)} required placeholder="Street, area (min. 3 characters)" />
        <div className="grid grid-cols-2 gap-3">
          <Field label="City" value={city} onChange={mark("city", setCity)} required />
          <Field label="Delivery date" value={date} onChange={mark("date", setDate)} type="date" required />
        </div>
        <Field label="Your name (sender)" value={sender} onChange={mark("sender", setSender)} required placeholder="From" />
        <label className="block">
          <span className="text-xs font-medium text-[#494550]">Gift message (optional)</span>
          <textarea
            value={message}
            onChange={(e) => {
              edited.current.add("message");
              setMessage(e.target.value);
            }}
            rows={2}
            placeholder="A short note for the card"
            className="mt-1 w-full resize-none rounded-lg border border-[#402970]/12 bg-[#F0EEFA]/40 px-3 py-2 text-sm text-[#222222] placeholder:text-[#494550]/50 focus:border-[#402970]/30 focus:bg-white focus:outline-none"
          />
        </label>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!ready || pending}
          className="w-full rounded-xl bg-[#402970] px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#2a1059] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {pending && submitting ? "Placing order…" : pending ? "Try again" : "Place order"}
        </button>
        <p className="text-center text-[11px] text-[#494550]/70">
          No charge yet — you'll get a secure Kapruka payment link to confirm.
        </p>
      </div>
    </motion.section>
  );
}
