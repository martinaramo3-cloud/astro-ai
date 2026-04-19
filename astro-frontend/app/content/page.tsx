import { getServerBackendBase } from "../../lib/api";

async function getContentLibrary() {
  const apiUrl = getServerBackendBase();
  const response = await fetch(`${apiUrl}/content-library`, { cache: "no-store" });
  if (!response.ok) throw new Error("Could not load astrology content library.");
  return response.json();
}

function SectionTitle({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <div className="max-w-3xl">
      <p className="text-sm uppercase tracking-[0.24em] text-white/45">{eyebrow}</p>
      <h1 className="mt-3 text-4xl font-semibold text-white">{title}</h1>
      <p className="mt-4 text-base leading-8 text-white/70">{text}</p>
    </div>
  );
}

export default async function ContentPage() {
  const data = await getContentLibrary();
  const planets = Object.entries(data.planets) as [string, { function: string; category: string }][];
  const signs = Object.entries(data.signs) as [string, { style: string; element: string; modality: string; strengths?: string[] }][];
  const houses = Object.entries(data.houses) as [string, { area: string }][];
  const relationshipRules = Object.entries(data.relationship_rules) as [string, string[]][];

  return (
    <main className="px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl space-y-10">
        <SectionTitle
          eyebrow="The method"
          title="Your astrology engine, presented like a real brand."
          text="This page turns your structured astrology material into a polished method page. Behind the scenes, the content still lives in editable files, but here it reads like a real website instead of raw data."
        />

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="glass rounded-[2rem] p-7">
            <h2 className="text-2xl font-semibold">How readings are built</h2>
            <ol className="mt-5 grid gap-3 text-sm leading-7 text-white/76 md:grid-cols-2">
              {data.interpretation_order.map((item: string, index: number) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">{index + 1}. {item}</li>
              ))}
            </ol>
          </div>
          <div className="glass rounded-[2rem] p-7">
            <h2 className="text-2xl font-semibold">Writing style</h2>
            <p className="mt-5 text-sm leading-7 text-white/76">The site uses a controlled interpretation formula so each reading has structure, consistency, and a more premium tone.</p>
            <div className="mt-5 rounded-3xl border border-white/10 bg-slate-950/55 p-5 text-sm leading-7 text-white/72">{data.output_templates.placement}</div>
          </div>
        </section>

        <section className="glass rounded-[2rem] p-7">
          <h2 className="text-2xl font-semibold">Core symbolism</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {planets.map(([name, details]) => (
              <article key={name} className="rounded-[1.6rem] border border-white/10 bg-slate-950/55 p-5">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-lg font-medium">{name}</h3>
                  <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-white/45">{details.category}</span>
                </div>
                <p className="mt-3 text-sm leading-7 text-white/74">{details.function}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="glass rounded-[2rem] p-7">
            <h2 className="text-2xl font-semibold">Signs as style</h2>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {signs.map(([name, details]) => (
                <article key={name} className="rounded-[1.6rem] border border-white/10 bg-slate-950/55 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-lg font-medium">{name}</h3>
                    <p className="text-xs uppercase tracking-[0.18em] text-white/45">{details.element} · {details.modality}</p>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-white/74">{details.style}</p>
                  {details.strengths?.length ? <p className="mt-3 text-xs uppercase tracking-[0.16em] text-violet-100/60">Strengths: {details.strengths.join(", ")}</p> : null}
                </article>
              ))}
            </div>
          </div>
          <div className="glass rounded-[2rem] p-7">
            <h2 className="text-2xl font-semibold">Relationship priorities</h2>
            <div className="mt-5 space-y-4">
              {relationshipRules.map(([topic, rules]) => (
                <div key={topic} className="rounded-[1.6rem] border border-white/10 bg-slate-950/55 p-5">
                  <h3 className="text-lg font-medium capitalize">{topic}</h3>
                  <p className="mt-3 text-sm leading-7 text-white/74">{rules.join(" · ")}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="glass rounded-[2rem] p-7">
          <h2 className="text-2xl font-semibold">Life areas</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {houses.map(([number, details]) => (
              <article key={number} className="rounded-[1.6rem] border border-white/10 bg-slate-950/55 p-5">
                <h3 className="text-lg font-medium">House {number}</h3>
                <p className="mt-3 text-sm leading-7 text-white/74">{details.area}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
