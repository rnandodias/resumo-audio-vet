# resumo-audio-vet

Transforma os áudios das aulas de uma pós-graduação em dermatologia veterinária em três materiais de estudo em Word por aula: `resumo.docx` (revisão rápida, ~10 páginas), `apostila.docx` (apostila enxuta, sem a transcrição) e `transcricao.docx` (transcrição integral limpa). Quem estuda é a aluna da pós; dinheiro não é restrição, qualidade vem primeiro.

## Método de trabalho

- **Sempre o venv do projeto (`.venv`), nunca o Python global.** Criar com `python -m venv .venv`; instalar com `.venv/Scripts/python -m pip install -r requirements.txt` (versões fixas). Todo comando roda com o venv.
- Cada rodada **abre** lendo este `CLAUDE.md` e `docs/CONTEXTO.md` e **fecha** com os dois atualizados, relatório detalhado em `docs/rodadas/rodada-NN.md`, commit e push.
- **Nunca reprocessar áudio já transcrito.** O cache das transcrições (`output/<slug>/transcricoes/*.json`) é achado pelo hash do áudio; se faltar, a chamada é paga de novo. Antes de repetir qualquer etapa já cacheada que custe dinheiro (apagar `.limpa.md`, arquivos de `secoes/` etc.), avisar e pedir confirmação.
- Relatório no chat: curto. O detalhe vai em `docs/rodadas/`.
- Código: um caminho só, sem camadas de reserva e sem código sem uso. Testes só onde pedido.

## Stack

- Python 3.12, `ffmpeg`/`ffprobe` no PATH (instalados via Chocolatey).
- AssemblyAI (`assemblyai` 1.8.2), modelo `universal-3-5-pro`, `language_code="pt"`, keyterms do glossário, diarização. O SDK 1.8.2 não conhece esse modelo no enum de resposta: ele monta a config e faz o upload; envio e polling usam o cliente HTTP autenticado do próprio SDK (ver `resumo/transcricao.py`).
- Anthropic (`anthropic` 2.3.0), modelo `claude-opus-5-5`, streaming, `max_tokens` 128000, thinking adaptativo, esforço `high` em todas as chamadas (`xhigh` não se usa), ferramenta `web_search_20260209` só no conteúdo da apostila (notas de verificação) e no material complementar.
- Word: pandoc empacotado no venv (`pypandoc_binary`) com o documento de referência `resumo/referencia.docx` (tabelas com grade e cabeçalho em negrito, fonte Aptos, pt-BR; para mudar o visual, editar os estilos dele no Word), conferido com `python-docx`.
- Chaves em `.env` (`ASSEMBLYAI_API_KEY`, `ANTHROPIC_API_KEY`); modelo em `.env.example`.

## Como rodar

```
.venv/Scripts/python run.py --aula "Anatomia Dermatológica"
.venv/Scripts/python -m pytest
```

Os áudios da aula ficam em `input/` (fora do git). A saída vai para `output/<slug-da-aula>/`:

| Caminho | O que é | No git |
|---|---|---|
| `manifesto.json` | áudios em ordem, hashes, duplicatas, avisos, consumo e custo por chamada | sim |
| `transcricao.md`, `.docx` | transcrição integral limpa, montada sem API | sim |
| `resumo.md`, `.docx` | resumo de revisão rápida | sim |
| `apostila.md`, `.docx` | apostila enxuta | sim |
| `apostila-completa.md`, `.docx`, `secoes-completa/` | apostila longa da rodada 1, só na aula "Anatomia Dermatológica", guardada para comparação; não é regerada | sim |
| `transcricoes/NN-<hash12>.bruta.md` / `.limpa.md` | transcrição bruta e limpa por áudio | sim |
| `secoes/*.md`, `*.urls.json`, `contexto.sha256` | cache das chamadas do resumo e da apostila (cada `.md` é uma chamada paga), URLs que a busca retornou para cada uma e assinatura das transcrições/instruções que as geraram | sim |
| `transcricoes/NN-<hash12>.json` | retorno completo da AssemblyAI (cache) | não |
| `audio/`, `log.txt` | áudio extraído (FLAC mono 16 kHz) e log | não |

Para regerar o resumo ou uma seção da apostila, apague o `.md` dela em `secoes/` (custa uma chamada). O glossário `glossario/dermato-vet.txt` serve de keyterms (limite da API: 1.000 palavras somadas, até 6 por termo) e de referência de grafia; amplie a cada aula.

## Pipeline (`run.py` → `resumo/`)

1. `audios.py`: varre `input/`, ordena pelo `creation_time` (fallback: data de modificação, com aviso), deduplica pelo SHA-256 do stream de áudio (não do arquivo: o WhatsApp muda bytes de metadados em cópias do mesmo áudio), extrai FLAC mono 16 kHz.
2. `transcricao.py`: AssemblyAI com cache por hash e retomada de job pendente (`.pendente`).
3. `limpeza.py`: Opus 5.5 limpa cada transcrição, uma chamada por áudio; falha se a limpa encolher mais de 30% em palavras.
4. `material.py`: `transcricao.md` montada localmente (capa e transcrição limpa de cada áudio). Também a base das chamadas pagas: o mesmo prefixo em cache (instruções, glossário e transcrições inteiras, TTL 1 h) para resumo e apostila, uma seção por arquivo em `secoes/`, assinatura do contexto e remoção dos links que a busca não retornou.
5. `resumo.py`: uma chamada, sem busca web, alvo de 3.000 a 3.500 palavras.
6. `apostila.py`: plano em 2 a 4 partes, depois cada parte (cerca de 8.500 palavras somadas, no máximo 6 notas de verificação por aula) e cada seção em chamadas separadas; capa montada localmente. Com a busca ligada o prefixo em cache é outro (as ferramentas vêm antes do `system`), por isso a primeira chamada com busca roda antes das demais com busca.

`word.py` converte cada `.md` com a referência e confere o `.docx` contra o Markdown: capa, títulos de nível 1, tabelas com grade e links.

## Estado atual

Rodada 02 concluída: três materiais por aula (resumo, apostila enxuta, transcrição), gerados para a aula "Anatomia Dermatológica" (23/10/2026), que guarda também a apostila completa da rodada 1 para comparação. Próximo passo: avaliação da aluna e, depois, a aplicação na VPS. Detalhes em `docs/CONTEXTO.md` e `docs/rodadas/rodada-02.md`.
