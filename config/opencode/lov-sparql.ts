import { tool } from "@opencode-ai/plugin"

// LOV (Linked Open Vocabularies) RDF vocabulary search.
// Queries the LOV SPARQL endpoint at https://lov.linkeddata.es/dataset/sparql
// and returns matching RDF vocabularies (URI, prefix, title, description).
//
// Self-contained: only uses the global `fetch`. Does NOT depend on the
// opencode-search plugin, websearch, or any other tool. Ships standalone.

const ENDPOINT = process.env.LOV_SPARQL_ENDPOINT || "https://lov.linkeddata.es/dataset/sparql"
const TIMEOUT_S = Math.min(Number(process.env.LOV_SPARQL_TIMEOUT || "30"), 120)

const SPARQL = (q: string) => ENDPOINT + "?query=" + encodeURIComponent(q)

// SPARQL query that lists vocabularies whose title or description matches a
// keyword (case-insensitive). Returns URI, prefix, title and description,
// deduplicated on the vocabulary URI. The keyword is split into tokens that
// are AND-joined; an empty keyword lists the most recent vocabularies.
function buildQuery(keyword: string, limit: number): string {
  const tokens = keyword.trim().split(/\s+/).filter(Boolean)
  const filters = tokens
    .map((t) => `CONTAINS(LCASE(CONCAT(COALESCE(?title,""), " ", COALESCE(?desc,""))), LCASE("${t.replace(/"/g, "")}"))`)
    .join(" && ")
  return `
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX voaf: <http://purl.org/vocommons/voaf#>
SELECT DISTINCT ?vocab ?prefix ?title ?desc WHERE {
  ?vocab a voaf:Vocabulary .
  ?vocab dct:title ?title .
  OPTIONAL { ?vocab voaf:preferredNamespacePrefix ?prefix }
  OPTIONAL { ?vocab dct:description ?desc }
  FILTER(LANG(?title) = 'en')
  ${filters ? `FILTER(${filters})` : ""}
}
LIMIT ${limit}`
}

interface Binding { type: string; value: string; "xml:lang"?: string }
interface Results {
  results: { bindings: Array<Record<string, Binding>> }
}

function val(b?: Binding): string {
  return b ? b.value : ""
}

export default tool({
  description:
    "Search the Linked Open Vocabularies (LOV) registry for RDF vocabularies. " +
    "Use this whenever the user asks for RDF vocabularies, vocabularies, ontologies, " +
    "or RDF schemas/terms - in ADDITION to (not instead of) any web search. " +
    "Returns matching vocabularies with their URI, prefix, title and description.",
  args: {
    keyword: tool.schema
      .string()
      .describe("Free-text keyword to search for (e.g. 'person', 'time', 'geo'). Multiple words are AND-joined. Empty lists recent vocabularies."),
    limit: tool.schema.number().optional().describe("Max vocabularies to return (default 10, max 50)."),
  },
  async execute(args) {
    const limit = Math.min(Math.max(args.limit ?? 10, 1), 50)
    const query = buildQuery(args.keyword, limit)
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_S * 1000)
    try {
      const res = await fetch(SPARQL(query), {
        signal: ctrl.signal,
        headers: { Accept: "application/sparql-results+json" },
      })
      if (!res.ok) {
        const txt = await res.text().catch(() => "")
        return `LOV SPARQL error ${res.status} ${res.statusText}: ${txt.slice(0, 500)}`
      }
      const json = (await res.json()) as Results
      const rows = (json.results?.bindings) || []
      if (!rows.length) return `No LOV vocabularies matched "${args.keyword}".`
      // Deduplicate on vocab URI, keep the first English description.
      const seen = new Set<string>()
      const out: string[] = []
      for (const b of rows) {
        const uri = val(b.vocab)
        if (!uri || seen.has(uri)) continue
        seen.add(uri)
        const prefix = val(b.prefix)
        const title = val(b.title)
        const desc = val(b.desc)
        out.push(
          `## ${title || "(untitled)"}\n` +
          `- URI: ${uri}` +
          (prefix ? `\n- prefix: ${prefix}` : "") +
          (desc ? `\n- description: ${desc}` : "")
        )
      }
      return `LOV vocabularies matching "${args.keyword}" (${out.length}):\n\n${out.join("\n\n")}`
    } catch (e: any) {
      return `LOV SPARQL query failed: ${e?.message ?? e}`
    } finally {
      clearTimeout(timer)
    }
  },
})
