# Round 1 seat status

| model | ok | ms | chars | error |
|---|---|---|---|---|
| openrouter:openai/gpt-5.6-terra | true | 84462 | 18653 | |
| openrouter:x-ai/grok-4.5 | true | 145954 | 14938 | |
| openrouter:z-ai/glm-5.2 | true (after retry) | 36951 | 7200 | initial run returned 328 chars (<400, counted failed); retried once with --max-tokens 7000 |
| openrouter:deepseek/deepseek-v4-flash-0731 | true | 124207 | 42454 | |

ok_count: 4/4

Seat files: ~/Documents/cairn/research/convergence/r1/seats/
- openrouter-openai-gpt-5-6-terra.md
- openrouter-x-ai-grok-4-5.md
- openrouter-z-ai-glm-5-2.md (overwritten by retry)
- openrouter-deepseek-deepseek-v4-flash-0731.md

## Commands run

```bash
mkdir -p ~/Documents/cairn/research/convergence/r1/seats
bun ~/.claude/scripts/multi-model.ts review --doc ~/Documents/cairn/research/convergence/plan-r0.md --prompt-file ~/Documents/cairn/research/convergence/review-prompt.md --out ~/Documents/cairn/research/convergence/r1/seats --max-tokens 10000 --json > ~/Documents/cairn/research/convergence/r1/seats.json 2> ~/Documents/cairn/research/convergence/r1/seats.log
bun ~/.claude/scripts/multi-model.ts review --doc ~/Documents/cairn/research/convergence/plan-r0.md --prompt-file ~/Documents/cairn/research/convergence/review-prompt.md --out ~/Documents/cairn/research/convergence/r1/seats --max-tokens 7000 --models "openrouter:z-ai/glm-5.2" --json > ~/Documents/cairn/research/convergence/r1/retry-glm-5-2.json 2>> ~/Documents/cairn/research/convergence/r1/seats.log
```
