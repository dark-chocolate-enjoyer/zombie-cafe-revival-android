// Builds the project website from the Markdown pages in this folder.
// GitHub Actions runs it on every push to main (.github/workflows/pages.yml) and publishes _build/.
// Local preview: cd site && npm ci && node build.mjs  ->  open _build/index.html
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(here, '_build');
const REPO = 'https://github.com/dark-chocolate-enjoyer/zombie-cafe-revival-android';
const MERMAID = 'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs';

const pages = [
  { src: 'ai-workflow.md', out: 'index.html', nav: 'AI workflow' },
  { src: 'technical-writeup.md', out: 'technical-writeup.html', nav: 'Technical write-up', toc: true },
];
const outName = Object.fromEntries(pages.map(p => [p.src, p.out]));

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const strip = s => s.replace(/<[^>]+>/g, '').replace(/&[a-z#0-9]+;/gi, ' ');
let seen, headings, usesMermaid;
const slug = raw => {
  let s = strip(raw).toLowerCase().replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-');
  seen[s] = (seen[s] ?? -1) + 1;
  return seen[s] ? `${s}-${seen[s]}` : s;
};

marked.use({
  gfm: true,
  renderer: {
    heading(text, level, raw) {
      if (level === 1) return `<h1>${text}</h1>\n`;
      const id = slug(raw);
      headings.push({ level, id, text: strip(text) });
      return `<h${level} id="${id}"><a class="anchor" href="#${id}" aria-hidden="true">#</a>${text}</h${level}>\n`;
    },
    code(code, lang) {
      if (lang === 'mermaid') { usesMermaid = true; return `<figure class="diagram"><pre class="mermaid">${esc(code)}</pre></figure>\n`; }
      return `<pre><code>${esc(code)}</code></pre>\n`;
    },
    table(header, body) {
      const firsts = [...body.matchAll(/<tr>\s*<td[^>]*>([\s\S]*?)<\/td>/g)].map(m => strip(m[1]).trim());
      const cls = firsts.every(t => t.length <= 12) ? ' class="short-first"' : '';
      return `<div class="table-wrap"><table${cls}><thead>${header}</thead><tbody>${body}</tbody></table></div>\n`;
    },
    link(href, title, text) {
      const local = outName[href.split('#')[0]];
      const target = local ? local + (href.includes('#') ? href.slice(href.indexOf('#')) : '') : href;
      const ext = /^https?:/.test(target) ? ' rel="noopener"' : '';
      return `<a href="${esc(target)}"${title ? ` title="${esc(title)}"` : ''}${ext}>${text}</a>`;
    },
  },
});

function render(page) {
  seen = {}; headings = []; usesMermaid = false;
  const md = fs.readFileSync(path.join(here, page.src), 'utf8');
  const title = md.match(/^# (.+)$/m)[1].trim();
  let body = marked.parse(md);
  // The first paragraph under the title is the page's lead; the rule after it only separates it in Markdown.
  body = body.replace(/(<\/h1>\n)<p>/, '$1<p class="lead">').replace(/(<p class="lead">[\s\S]*?<\/p>\n)<hr>\n/, '$1');
  const lead = strip(body.match(/<p class="lead">([\s\S]*?)<\/p>/)?.[1] ?? '').replace(/\s+/g, ' ').trim();
  if (page.toc) {
    const items = headings.filter(h => h.level <= 3)
      .map(h => `<li class="l${h.level}"><a href="#${h.id}">${esc(h.text)}</a></li>`).join('');
    body = body.replace(/(<p class="lead">[\s\S]*?<\/p>\n)/, `$1<nav class="toc" aria-label="On this page"><p>On this page</p><ul>${items}</ul></nav>\n`);
  }
  const nav = pages.map(p => `<a href="${p.out}"${p === page ? ' aria-current="page"' : ''}>${p.nav}</a>`).join('');
  return `<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} · Zombie Cafe Revival</title>
<meta name="description" content="${esc(lead)}">
<meta property="og:title" content="${esc(title)} · Zombie Cafe Revival">
<meta property="og:description" content="${esc(lead)}">
<meta property="og:type" content="article">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site">
  <div class="bar">
    <a class="brand" href="index.html">Zombie Cafe Revival</a>
    <nav>${nav}<a href="${REPO}" rel="noopener">GitHub</a></nav>
  </div>
</header>
<main>
${body}
</main>
<footer class="site">
  <p><a href="${REPO}" rel="noopener">Source on GitHub</a>. These pages are built from Markdown by GitHub Actions on every push.</p>
  <p><i>Zombie Cafe</i> © Capcom / Beeline Interactive. Fan preservation project, not affiliated with Capcom.</p>
</footer>
${usesMermaid ? `<script type="module">
import mermaid from '${MERMAID}';
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const css = getComputedStyle(document.documentElement);
const v = n => css.getPropertyValue(n).trim();
mermaid.initialize({
  startOnLoad: true, securityLevel: 'strict', theme: 'base', flowchart: { wrappingWidth: 360 },
  themeVariables: {
    darkMode: dark, fontFamily: v('--font'), fontSize: '14px',
    primaryColor: v('--node'), primaryTextColor: v('--text'), primaryBorderColor: v('--node-border'),
    lineColor: v('--muted'), textColor: v('--text'), clusterBkg: v('--cluster'), clusterBorder: v('--border'),
    edgeLabelBackground: v('--bg'), titleColor: v('--text'),
  },
});
</script>` : ''}
</body>
</html>
`;
}

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
fs.copyFileSync(path.join(here, 'style.css'), path.join(out, 'style.css'));
for (const page of pages) {
  fs.writeFileSync(path.join(out, page.out), render(page));
  console.log(`built ${page.out} from ${page.src}`);
}
