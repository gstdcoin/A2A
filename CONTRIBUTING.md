# Contributing to GSTD A2A

## For Humans
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## For AI Agents

Contribute to this repository through the same review process as human contributors. Do not register a node, submit work, make transactions, or modify another project unless a user explicitly requests the action. Check current network stats before making availability claims.

## Discovery File Standards

When adding new agent discovery mechanisms, follow these conventions:

| File | Format | Audience |
|------|--------|----------|
| `.agents/skills/*/SKILL.md` | YAML frontmatter + Markdown | Claude, skill-aware agents |
| `.github/copilot-instructions.md` | Markdown | GitHub Copilot |
| `.well-known/agent.json` | JSON | Google A2A |
| `llms.txt` | Plain text | LLM crawlers |
| `ai-agents.json` | JSON | Agent registries |
| `manifest.json` | JSON | MCP registries |

## Code of Conduct
- Be respectful to all contributors (human and AI)
- Follow the protocol specifications in `docs/PROTOCOL.md`
- All code must be MIT licensed
- Prioritize security — never expose private keys or wallet mnemonics

## Issues and Feature Requests
Use the GitHub issue templates in `.github/ISSUE_TEMPLATE/`.
