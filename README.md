# Sixtyfour Skills

[Agent Skills](https://github.com/anthropics/skills) that teach AI coding assistants (Claude Code, Cursor, etc.) how to use [Sixtyfour](https://sixtyfour.ai) — people and company intelligence at scale.

## Skills

| Skill | Description |
|-------|-------------|
| [sixtyfour](./skills/sixtyfour) | Find people, enrich contacts, research companies, build prospect lists, and run data enrichment workflows via the Sixtyfour API. |

## Installation

### Claude Code

Add the skill to your project:

```bash
npx skills add sixtyfour-ai/skills --skill "sixtyfour"
```

Or link it directly:

```bash
# Clone this repo
git clone https://github.com/sixtyfour-ai/skills.git /path/to/sixtyfour-skills

# Symlink into your project
ln -s /path/to/sixtyfour-skills/skills/sixtyfour .claude/skills/sixtyfour
```

### Cursor

Install as a [Cursor plugin](https://cursor.com/docs/plugins):

```
/add-plugin sixtyfour
```

### Manual

Copy the `skills/sixtyfour` directory into your agent's skills directory.

## Prerequisites

1. **Sign up** at [app.sixtyfour.ai](https://app.sixtyfour.ai)
2. **Generate an API key** at [app.sixtyfour.ai/keys](https://app.sixtyfour.ai/keys)
3. **Set the environment variable**:

```bash
export SIXTYFOUR_API_KEY=your_key_here
```

## Usage

Once installed, your agent can:

- **Find emails and phones** — "Find the email for Sarah Chen at Figma"
- **Enrich people** — "What's Jane Doe's title, LinkedIn, and years of experience at Acme Corp?"
- **Research companies** — "Tell me about Ramp — revenue, headcount, funding, engineering leadership"
- **Search at scale** — "Find 500 VPs of Sales at Series B SaaS startups in NYC"
- **Build workflows** — "Search for AI startups, find their CTOs, get emails, and export to CSV"
- **Reverse lookups** — "Who owns the email cto@startup.io?"

## Documentation

- [Sixtyfour Docs](https://docs.sixtyfour.ai)
- [API Quick Start](https://docs.sixtyfour.ai/api-quick-start)
- [Skills Guide](https://docs.sixtyfour.ai/developer-tools/skills)

## Feedback

Something not working? [Open an issue](https://github.com/sixtyfour-ai/skills/issues).
