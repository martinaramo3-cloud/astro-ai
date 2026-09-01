"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

/**
 * Thumbnails for the images sent with a message.
 *
 * They're fetched rather than linked: the endpoint needs a bearer token, and
 * an `<img src>` can't send one. Putting the image behind a guessable public
 * URL instead would mean a screenshot of someone's messages was one lucky id
 * away from anyone — so it stays authenticated, and this pays a fetch for it.
 */
export default function AttachedImages({ ids }: { ids: number[] }) {
  const [urls, setUrls] = useState<Record<number, string>>({});
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const made: string[] = [];

    (async () => {
      for (const id of ids) {
        try {
          const res = await apiFetch(`/attachments/${id}`);
          if (!res.ok) continue;
          const url = URL.createObjectURL(await res.blob());
          made.push(url);
          if (cancelled) break;
          setUrls((prev) => ({ ...prev, [id]: url }));
        } catch {
          /* a missing image shouldn't break the transcript around it */
        }
      }
    })();

    return () => {
      cancelled = true;
      made.forEach(URL.revokeObjectURL);
    };
  }, [ids]);

  if (!ids.length) return null;

  return (
    <>
      <div className="mb-2 flex flex-wrap justify-end gap-2">
        {ids.map((id) =>
          urls[id] ? (
            <button
              key={id}
              onClick={() => setOpen(urls[id])}
              aria-label="View full size"
              style={{
                borderRadius: 14,
                overflow: "hidden",
                border: "1px solid var(--line-2)",
                lineHeight: 0,
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={urls[id]}
                alt="Attached"
                style={{ maxWidth: 190, maxHeight: 190, display: "block" }}
              />
            </button>
          ) : (
            <div
              key={id}
              style={{
                width: 92,
                height: 92,
                borderRadius: 14,
                background: "var(--sunk)",
                border: "1px solid var(--line-2)",
              }}
            />
          ),
        )}
      </div>

      {open && (
        <div
          className="fixed inset-0 z-[80] flex items-center justify-center p-6"
          style={{ background: "rgba(0,0,0,0.8)" }}
          onClick={() => setOpen(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={open}
            alt="Attached, full size"
            style={{ maxWidth: "100%", maxHeight: "100%", borderRadius: 12 }}
          />
        </div>
      )}
    </>
  );
}
