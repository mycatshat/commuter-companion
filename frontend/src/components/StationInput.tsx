import { useEffect, useRef, useState } from "react";
import { searchStations, type StationSearchResult } from "../api";

interface Props {
  label: string;
  placeholder: string;
  value: string;
  onChange: (stationName: string) => void;
}

/**
 * Station-name autocomplete backed by /api/stations/search. Debounced by
 * hand (no extra dependency for something this small) -- 200ms after the
 * user stops typing, not on every keystroke, so a phone on a slow
 * connection isn't firing a request per character.
 */
export default function StationInput({ label, placeholder, value, onChange }: Props) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<StationSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query || query === value) {
      setResults([]);
      return;
    }
    const thisRequest = ++requestIdRef.current;
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchStations(query);
        if (requestIdRef.current === thisRequest) setResults(res);
      } catch {
        if (requestIdRef.current === thisRequest) setResults([]);
      }
    }, 200);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <div className="station-input">
      <label className="station-input-label">{label}</label>
      <input
        type="text"
        inputMode="search"
        autoComplete="off"
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)} // let a click on a suggestion register first
      />
      {open && results.length > 0 && (
        <div className="station-suggestions" role="listbox">
          {results.map((r) => (
            <button
              key={r.name}
              type="button"
              className="station-suggestion"
              onMouseDown={(e) => e.preventDefault()} // keep focus so onBlur doesn't close before onClick fires
              onClick={() => {
                onChange(r.name);
                setQuery(r.name);
                setResults([]);
                setOpen(false);
              }}
            >
              <span className="station-suggestion-name">{r.name}</span>
              <span className="station-suggestion-lines">{r.lines.join(", ")}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
