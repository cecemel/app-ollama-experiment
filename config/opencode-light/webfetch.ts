import { tool } from "@opencode-ai/plugin"

// Custom webfetch tool: same name as the built-in, so it takes precedence. The only
// reason it exists is to send a normal Firefox User-Agent (the built-in sends Chrome /
// "opencode", which some sites block). Override the UA with WEBFETCH_USER_AGENT.
const UA =
  process.env.WEBFETCH_USER_AGENT ||
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"
const MAX_BYTES = 5 * 1024 * 1024

const strip = (s: string) => s.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim()

function htmlToText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, "")
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi, (_m, l, t) => `\n${"#".repeat(Number(l))} ${strip(t)}\n`)
    .replace(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi, (_m, h, t) => `${strip(t)} (${h})`)
    .replace(/<li\b[^>]*>/gi, "\n- ")
    .replace(/<\/(p|div|section|article|tr|h[1-6]|ul|ol|li)>/gi, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&#x27;/gi, "'")
    .replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").replace(/[ \t]{2,}/g, " ")
    .trim()
}

export default tool({
  description:
    "Fetch a URL and return its content as text/markdown or raw html. Sends a normal Firefox User-Agent so sites that block non-browser clients still load.",
  args: {
    url: tool.schema.string().describe("The URL to fetch"),
    format: tool.schema.enum(["text", "markdown", "html"]).optional().describe("Output format (default markdown)"),
    timeout: tool.schema.number().optional().describe("Timeout in seconds (max 120)"),
  },
  async execute(args) {
    const format = args.format ?? "markdown"
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), Math.min(args.timeout ?? 30, 120) * 1000)
    try {
      const res = await fetch(args.url, {
        signal: ctrl.signal,
        redirect: "follow",
        headers: {
          "User-Agent": UA,
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.5",
          "Accept-Encoding": "gzip, deflate, br",
          "Sec-Fetch-Dest": "document",
          "Sec-Fetch-Mode": "navigate",
          "Sec-Fetch-Site": "none",
          "Sec-Fetch-User": "?1",
          "Upgrade-Insecure-Requests": "1",
          "DNT": "1",
          "Connection": "keep-alive",
        },
      })
      if (!res.ok) return `Error: ${res.status} ${res.statusText} fetching ${args.url}`
      let body = await res.text()
      if (body.length > MAX_BYTES) body = body.slice(0, MAX_BYTES) + "\n[... truncated]"
      return format === "html" ? body : htmlToText(body)
    } catch (e: any) {
      return `Error fetching ${args.url}: ${e?.message ?? e}`
    } finally {
      clearTimeout(timer)
    }
  },
})
