# Sixtyfour Skills

[Agent Skills](https://github.com/anthropics/skills) that teach AI coding assistants (Claude Code, Cursor, etc.) how to use [Sixtyfour](https://sixtyfour.ai) — people and company intelligence at scale.

## Skills

| Skill | Description |
|-------|-------------|
| [sixtyfour](./skills/sixtyfour) | People and company intelligence — investigate any person or company, resolve identities, map relationships, and surface signals via the Sixtyfour API. |

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

- **Investigate people** — "Tell me everything about Jane Doe at Acme Corp — title, background, LinkedIn, career trajectory"
- **Research companies** — "Research Ramp — revenue, headcount, funding, engineering leadership"
- **Search at scale** — "Find 500 VPs of Sales at Series B SaaS startups in NYC"
- **Build pipelines** — "Search for AI startups, find their CTOs, get contact info, and export to CSV"
- **Due diligence** — "Deep investigation on this person for compliance review" (medium/high tier)

## Documentation

- [Sixtyfour Docs](https://docs.sixtyfour.ai)
- [API Quick Start](https://docs.sixtyfour.ai/api-quick-start)
- [Skills Guide](https://docs.sixtyfour.ai/developer-tools/skills)

## Development

### Versioning

Both Claude Code and Cursor use semantic versioning in the manifest files — not git tags. Bump the version in all three manifest files before pushing:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.cursor-plugin/plugin.json`

Git tags are optional — useful for tracking releases on GitHub but not required by either platform.

### Updating

**Claude Code** — version-based, no manual review. Push to `main` and users run:
```bash
claude plugin update sixtyfour@sixtyfour-skills
```
A restart is required to apply the update.

**Cursor** — updates go through manual marketplace review before publishing. Cursor caches installed versions locally, so users generally need to uninstall and reinstall the plugin via the in-app marketplace to get the latest version.

## Feedback

Something not working? [Open an issue](https://github.com/sixtyfour-ai/skills/issues).


## Feedback

Something not working? [Open an issue](https://github.com/sixtyfour-ai/skills/issues).
