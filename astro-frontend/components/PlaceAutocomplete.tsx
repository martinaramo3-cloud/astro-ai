"use client";

import { useEffect, useRef, useState } from "react";
import { getBrowserApiBase } from "../lib/api";

/**
 * A birthplace, named the way a person would name it.
 *
 * This used to query a different geocoder than the one that resolves the
 * chart, and show whatever raw string came back — "Tirana, Bashkia Tiranë,
 * Qarku i Tiranës, 1001, Albania". Nobody recognises their birthplace in that,
 * and the two services could disagree, so the place picked was not necessarily
 * the place used. It now asks our own server, which asks the geocoder the
 * chart uses, and gets back "Tirana, Albania".
 */
interface Suggestion {
  label: string;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  style?: React.CSSProperties;
}

export default function PlaceAutocomplete({ value, onChange, placeholder = "Birth place, e.g. Paris, France", className, style }: Props) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    onChange(val);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (val.trim().length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `${getBrowserApiBase()}/places/suggest?q=${encodeURIComponent(val)}`,
        );
        const data = await res.json();
        const places: Suggestion[] = data.places ?? [];
        setSuggestions(places);
        setOpen(places.length > 0);
      } catch {
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 400);
  };

  const handleSelect = (suggestion: Suggestion) => {
    // The label is already what should be stored — no trimming to the first
    // two commas, which is what turned Tirana into "Tirana, Bashkia Tiranë".
    onChange(suggestion.label);
    setSuggestions([]);
    setOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        value={value}
        onChange={handleInput}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        placeholder={placeholder}
        className={className}
        style={style}
        autoComplete="off"
      />
      {loading && (
        <div
          className="absolute right-4 top-1/2 -translate-y-1/2 text-xs"
          style={{ color: "var(--ink-3)" }}
        >
          searching...
        </div>
      )}
      {open && suggestions.length > 0 && (
        <ul
          className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: 14,
            boxShadow: "var(--shadow)",
          }}
        >
          {suggestions.map((s) => (
            <li key={s.label}>
              <button
                type="button"
                onMouseDown={() => handleSelect(s)}
                className="w-full px-4 py-3 text-left text-sm"
                style={{ color: "var(--ink-2)" }}
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
