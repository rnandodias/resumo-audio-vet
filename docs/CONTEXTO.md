# Contexto e decisões

Registro das decisões do projeto e do que vem a seguir. Atualizado ao fim de cada rodada.

## Decisões

| Data | Decisão | Motivo |
|---|---|---|
| 01/11/2026 | **AssemblyAI** para transcrição, modelo `universal-3-5-pro` (o mais preciso da API assíncrona; o `universal-3-pro` foi descontinuado), português, keyterms e diarização | Precisão em áudio ruidoso em português, gravado por celular a distância do professor. Keyterms (até 1.000 palavras) e `prompt` são mutuamente exclusivos nesse modelo; escolhemos keyterms, que ataca diretamente os termos técnicos |
| 01/11/2026 | **Uma apostila por aula**, não por áudio | A aula é uma unidade; os áudios são cortes arbitrários da gravação. A apostila consolida os áudios como uma aula só |
| 01/11/2026 | **Ordem pela data de gravação** (`creation_time` do arquivo) | O nome dos arquivos do WhatsApp é a hora da exportação e não serve para ordenar |
| 01/11/2026 | **Deduplicação pelo hash do stream de áudio**, não do arquivo | A duplicata conhecida da aula 1 difere em 6 bytes de metadados do MP4; o áudio é idêntico |
| 01/11/2026 | ~~Estrutura da apostila~~ (substituída na rodada 02): capa; resumo executivo; conteúdo por tópicos na ordem da aula; pontos enfatizados/prova; glossário; dúvidas em aberto; questões com gabarito comentado; material complementar (só links retornados pela busca); anexo com a transcrição integral limpa por áudio | Aprovada pelo usuário antes da rodada 01 |
| 01/11/2026 | **Opus 5.5** (`claude-opus-5-5`) na limpeza e na apostila, `max_tokens` 128000, busca web nativa na apostila | Qualidade primeiro |
| 01/11/2026 | Limpeza: **uma chamada por áudio**, sem divisão em blocos; erro explícito se um áudio passar de 14 mil palavras brutas | Medido na aula 1: o maior áudio (48 min, 5.918 palavras) gastou no máximo ~40 mil tokens de saída (texto + raciocínio, até ~7 por palavra), bem abaixo dos 128 mil. 14 mil palavras (~2 h de fala) é o teto seguro; divisão em blocos seria código sem uso com áudios do WhatsApp |
| 01/11/2026 | Apostila **gerada por seções** com prefixo comum em cache | Cada parte do conteúdo tem a saída inteira do modelo à disposição; nenhuma seção fica rasa ou truncada |
| 01/11/2026 | Word via **pandoc empacotado no venv** (`pypandoc_binary`) | Pandoc não estava instalado no sistema; o pacote evita instalar software global e dá títulos navegáveis, sumário, tabelas e links reais |
| 01/11/2026 | **Aplicação web na VPS fica para depois** | Primeiro validar a apostila; só então construir app, banco e telas |
| 01/11/2026 | **Três materiais por aula**: `resumo.docx` (revisão rápida, alvo ~10 páginas, só o que foi dito, ênfases do professor em negrito), `apostila.docx` (enxuta) e `transcricao.docx` (transcrição integral limpa em arquivo próprio) | A apostila da rodada 1 (258 páginas) ficou grande demais para estudo semanal |
| 01/11/2026 | **Apostila enxuta**: capa; resumo executivo (meia página); conteúdo na ordem da aula com cerca de um terço do volume da rodada 1 (~8.500 palavras); pontos enfatizados; glossário dos termos centrais (50–70); dúvidas em aberto; 15 questões com gabarito; 10 itens de material complementar. Sem anexo de transcrição. No máximo 6 notas de verificação por aula, só quando a literatura contradiz ou muda o entendimento | Substitui a estrutura aprovada antes da rodada 01 |
| 01/11/2026 | A apostila da rodada 1 vira **`apostila-completa`**, só na aula "Anatomia Dermatológica", com as seções em `secoes-completa/`. Os dois deslizes da auditoria foram corrigidos à mão, sem API | A aluna vai comparar as duas versões |
| 01/11/2026 | **Esforço `high` em todas as chamadas** ao Opus 5.5; `xhigh` saiu do código. Busca web só no conteúdo da apostila (notas de verificação) e no material complementar | Custo: o `xhigh` respondia pela maior parte dos US$ 18,74 da apostila da rodada 1 |
| 01/11/2026 | Resumo e apostila compartilham o **mesmo prefixo em cache** e a mesma pasta `secoes/`, com a mesma assinatura do contexto | Uma escrita de cache para os dois materiais; mesma proteção contra reaproveitar seções geradas de transcrições diferentes |
| 01/11/2026 | **Documento de referência do Word** (`resumo/referencia.docx`): tabelas com grade, cabeçalho em negrito e sombreado, texto da tabela em 10 pt, fonte Aptos, idioma pt-BR. O conversor aceita listas sem linha em branco antes | Tabelas com bordas aprovadas na revisão da rodada 1; as listas saíam coladas no parágrafo |
| 01/11/2026 | Confirmados: limpeza sem blocos; pandoc via `pypandoc_binary`; sem modelo reserva; diarização e keyterms; duplicata fica a sem " (1)"; sumário do Word atualizado ao abrir; seções versionadas no git; OneDrive é ajuste na máquina, não no código | Respostas à lista "a confirmar" da rodada 1 |

## O que vem a seguir

1. A aluna avalia os três materiais da aula 1 e compara a apostila enxuta com a `apostila-completa`. Ajustes de tamanho e de prompt entram antes da aula 2.
2. Itens da lista "a confirmar" em `docs/rodadas/rodada-02.md`.
3. Próximas aulas: colocar os áudios em `input/` e rodar com o nome da aula; ampliar o glossário com os termos novos.
4. Aplicação na VPS para a aluna subir os áudios e dar nome às aulas, ainda a desenhar: upload, fila de processamento, histórico e download dos três materiais.
