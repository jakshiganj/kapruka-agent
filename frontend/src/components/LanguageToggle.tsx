import { LANGUAGES, LANGUAGE_LABELS, type Language } from "../i18n";

interface LanguageToggleProps {
  language: Language;
  onChange: (language: Language) => void;
}

export function LanguageToggle({ language, onChange }: LanguageToggleProps) {
  return (
    <div
      role="group"
      aria-label="Language"
      className="flex items-center gap-0.5 rounded-full border border-[#402970]/12 bg-[#F0EEFA] p-0.5"
    >
      {LANGUAGES.map((lang) => {
        const active = lang === language;
        return (
          <button
            key={lang}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(lang)}
            className={`rounded-full px-2.5 py-1 text-xs font-semibold transition-colors ${
              active
                ? "bg-[#402970] text-white"
                : "text-[#402970]/70 hover:text-[#402970]"
            }`}
          >
            {LANGUAGE_LABELS[lang]}
          </button>
        );
      })}
    </div>
  );
}
