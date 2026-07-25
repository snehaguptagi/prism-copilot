export interface Story {
  headline: string;
  body: string;
  stats: string[];
}

const STAT_RE =
  /(?:[+-]?\d[\d,.]*\s?%|₹\s?[\d,.]+\s?(?:crore|cr|lakh|trillion|billion)?|\$\s?[\d,.]+\s?(?:trillion|billion|million|bn|mn)?)/gi;

function extractStats(text: string): string[] {
  const found = text.match(STAT_RE) ?? [];
  const cleaned = found
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter((s) => s.length <= 18);
  return Array.from(new Set(cleaned)).slice(0, 3);
}

/** Split a Claude news narrative into individual story cards. The narratives
 * use "**N. Headline**" markers, so we split on those and pair each headline
 * with the text that follows it. Falls back to a single block if no markers. */
export function parseStories(narrative: string): Story[] {
  if (!narrative?.trim()) return [];

  const parts = narrative.split(/\*\*\s*(\d+\.\s*[^*]+?)\s*\*\*/g);
  const stories: Story[] = [];

  for (let i = 1; i < parts.length; i += 2) {
    const headline = parts[i].replace(/^\d+\.\s*/, "").replace(/[.:]\s*$/, "").trim();
    let body = (parts[i + 1] ?? "").trim();
    // strip any leading markdown emphasis / stray markers
    body = body.replace(/^\*+/, "").replace(/\n{3,}/g, "\n\n").trim();
    if (!headline) continue;
    stories.push({ headline, body, stats: extractStats(body) });
  }

  if (stories.length === 0) {
    // no numbered markers — treat the whole thing as one block, dropping the
    // model's conversational preamble line if present
    const body = narrative.replace(/^I'?ll research[^.]*\.\s*/i, "").trim();
    return [{ headline: "", body, stats: extractStats(body) }];
  }
  return stories;
}

export function sourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
