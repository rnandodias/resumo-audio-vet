# resumo-audio-vet

Transforma os áudios das aulas de uma pós-graduação em dermatologia veterinária em material de estudo: transcrição integral limpa e apostila completa em Word, uma apostila por aula. Quem estuda é a aluna da pós; dinheiro não é restrição, qualidade vem primeiro.

## Método de trabalho

- **Sempre o venv do projeto (`.venv`), nunca o Python global.** Criar com `python -m venv .venv`; instalar com `.venv/Scripts/python -m pip install -r requirements.txt` (versões fixas). Todo comando roda com o venv.
- Cada rodada **abre** lendo este `CLAUDE.md` e `docs/CONTEXTO.md` e **fecha** com os dois atualizados, relatório detalhado em `docs/rodadas/rodada-NN.md`, commit e push.
- **Nunca reprocessar áudio já transcrito.** O cache das transcrições (`output/<slug>/transcricoes/*.json`) é achado pelo hash do áudio; se faltar, a chamada é paga de novo. Antes de repetir qualquer etapa já cacheada que custe dinheiro (apagar `.limpa.md`, seções da apostila etc.), avisar e pedir confirmação.
- Relatório no chat: curto. O detalhe vai em `docs/rodadas/`.
- Código: um caminho só, sem camadas de reserva e sem código sem uso. Testes só onde pedido.

## Stack

- Python 3.12, `ffmpeg`/`ffprobe` no PATH (instalados via Chocolatey).
- AssemblyAI (`assemblyai` 1.8.2), modelo `universal-3-5-pro`, `language_code="pt"`, keyterms do glossário, diarização. O SDK 1.8.2 não conhece esse modelo no enum de resposta: ele monta a config e faz o upload; envio e polling usam o cliente HTTP autenticado do próprio SDK (ver `resumo/transcricao.py`).
- Anthropic (`anthropic` 2.3.0), modelo `claude-opus-5-5`, streaming, `max_tokens` 128000, thinking adaptativo, ferramenta `web_search_20260209` na apostila.
- Word: pandoc empacotado no venv (`pypandoc_binary`), conferido com `python-docx`.
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
| `apostila.md`, `apostila.docx` | a apostila | sim |
| `transcricoes/NN-<hash12>.bruta.md` / `.limpa.md` | transcrição bruta e limpa por áudio | sim |
| `secoes/*.md`, `*.urls.json`, `contexto.sha256` | cache das seções da apostila (cada uma é uma chamada paga), URLs que a busca retornou para cada uma e assinatura das transcrições/instruções que as geraram | sim |
| `transcricoes/NN-<hash12>.json` | retorno completo da AssemblyAI (cache) | não |
| `audio/`, `log.txt` | áudio extraído (FLAC mono 16 kHz) e log | não |

Para regerar uma seção da apostila, apague o `.md` dela em `secoes/` (custa uma chamada). O glossário `glossario/dermato-vet.txt` serve de keyterms (limite da API: 1.000 palavras somadas, até 6 por termo) e de referência de grafia; amplie a cada aula.

## Pipeline (`run.py` → `resumo/`)

1. `audios.py`: varre `input/`, ordena pelo `creation_time` (fallback: data de modificação, com aviso), deduplica pelo SHA-256 do stream de áudio (não do arquivo: o WhatsApp muda bytes de metadados em cópias do mesmo áudio), extrai FLAC mono 16 kHz.
2. `transcricao.py`: AssemblyAI com cache por hash e retomada de job pendente (`.pendente`).
3. `limpeza.py`: Opus 5.5 limpa cada transcrição, uma chamada por áudio; falha se a limpa encolher mais de 30% em palavras.
4. `apostila.py`: plano de tópicos, depois cada parte do conteúdo e cada seção em chamadas separadas com o mesmo prefixo em cache (transcrições inteiras, TTL 1 h); links que a busca não retornou são removidos; capa e anexo montados localmente. `word.py` converte e confere o `.docx`.

## Estado atual

Rodada 01 concluída: pipeline de ponta a ponta e primeira apostila (aula "Anatomia Dermatológica", 23/10/2026). Aguardando aprovação da apostila antes da aplicação web/VPS. Detalhes em `docs/CONTEXTO.md` e `docs/rodadas/rodada-01.md`.
