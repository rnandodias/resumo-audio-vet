# Rodada 02: resumo de revisão rápida, apostila menor e transcrição separada

**Data:** 01/11/2026 · **Modelo:** Opus 5.5, esforço `high` · **Aula:** Anatomia Dermatológica (gravada em 23/10/2026)

## Resultado

A partir desta rodada, `python run.py --aula "<nome>"` entrega três materiais por aula. A aula 1 guarda também a apostila longa da rodada 1, para comparação.

| Arquivo (em `output/anatomia-dermatologica/`) | Páginas no Word | Palavras (Word) | Títulos | Tabelas | Links |
|---|---|---|---|---|---|
| `resumo.docx` / `.md` | 19 | 4.690 | 64 | 17 | 0 |
| `apostila.docx` / `.md` | 62 | 18.244 | 152 | 44 | 16 |
| `transcricao.docx` / `.md` | 70 | 27.457 | 8 | 0 | 0 |
| `apostila-completa.docx` / `.md` (rodada 1) | 239 | 79.510 | 297 | 109 | 127 |

As páginas foram contadas pelo próprio Word: abri cada `.docx`, atualizei o sumário e exportei para PDF. As tabelas foram conferidas visualmente no PDF e têm grade, cabeçalho em negrito e sombreado. Os links clicáveis do Word batem com os do Markdown.

Nenhum áudio foi retranscrito nem relimpo. O manifesto continua com 8 registros da AssemblyAI e 8 de limpeza, e o log mostra as Etapas 1 a 3 inteiras no cache.

## O que foi feito

### 1. Apostila completa preservada e corrigida

- `apostila.md` e `apostila.docx` foram renomeados para `apostila-completa.*` (`git mv`), e `secoes/` foi movido para `secoes-completa/`.
- As duas frases da auditoria foram corrigidas à mão em `secoes-completa/`:
  - `conteudo-parte-04.md`, tabela do tricograma: "a confirmar por histopatologia" passou a "a confirmar com as células [?]" (Áudio 2, 00:28:13).
  - `pontos-enfatizados.md`, item 33: "Somente coxins (no homem e no cavalo, em toda a pele)" passou a "Somente coxins (o professor citou também homem e cavalo)" (Áudio 3, 00:22:23).
- A remontagem foi feita com o código da rodada 1, antes de ele ser reescrito, por um script descartável fora do repositório. O cliente da API era `None`, então qualquer tentativa de chamada quebraria em vez de cobrar.
- O diff de `apostila-completa.md` contra o `apostila.md` da rodada 1 tem exatamente 2 linhas, que são as duas frases. O Word tem os mesmos 297 títulos, 109 tabelas e 127 links.
- O número de páginas caiu de 258 para 239 só pela diagramação nova (texto das tabelas em 10 pt, menos espaço nas células). O conteúdo é o mesmo.

### 2. Tabelas com bordas e documento de referência

- `resumo/referencia.docx` foi feito a partir do `reference.docx` padrão do pandoc empacotado. As mudanças:
  - Estilo `Table` com grade cinza (todas as bordas, 0,5 pt) e margens nas células.
  - Texto da tabela em 10 pt.
  - Primeira linha em negrito, com fundo azul-claro e sem quebra entre ela e a linha seguinte.
  - Idioma pt-BR. A fonte segue a do tema, Aptos, a 12 pt no corpo.
- `word.py` usa a referência em todo `.docx`. A conferência agora compara o Word com o próprio Markdown, pelo AST do pandoc, e falha se:
  - não houver capa;
  - o número de títulos de nível 1 diferir do Markdown;
  - o número de tabelas diferir do Markdown;
  - alguma tabela estiver sem grade;
  - o conjunto de URLs diferir do Markdown.
- **Correção extra (não pedida):** o PDF da apostila completa mostrou listas coladas no parágrafo ("… autoimune. - O ataque …"). Isso acontece quando o modelo abre a lista sem linha em branco antes, e já vinha da rodada 1. O conversor passou a ler o Markdown com `lists_without_preceding_blankline`, o que vale para os três materiais e para a completa reconvertida (2.605 parágrafos, contra 2.572).

### 3. `transcricao.docx`

- É montada localmente em `material.transcricao_integral`, sem chamada de API.
- Começa por uma capa com nome da aula, subtítulo, data, duração total e número de áudios.
- Em seguida vem cada áudio sob o título "Áudio N (hh:mm de gravação, duração)", por exemplo "Áudio 1 (09:27 de gravação, 0:26:44)".

### 4. `resumo.docx`

- Uma chamada ao Opus 5.5, esforço `high`, `max_tokens` 128 mil, sem ferramentas. Cabe com folga: entrada de cerca de 80 mil tokens e 24 mil de saída, já contando o raciocínio.
- O pedido (`resumo/resumo.py`) segue a especificação:
  - só o que foi dito, na ordem da aula, sem deixar tópico de fora;
  - `#` para os blocos da aula e `##` para os tópicos;
  - frases curtas e tabelas para doses, classificações e comparações;
  - negrito só no que o professor enfatizou;
  - `[?]` mantido nos termos duvidosos;
  - nada de transcrição, questões, links, glossário, notas de verificação, tempos de áudio ou introduções.
- O cache é o mesmo das seções: `secoes/resumo.md`, sob a mesma assinatura de contexto da apostila.
- O resumo e a apostila usam o mesmo system prompt e o mesmo prefixo de transcrições. O resumo grava o cache de 1 h, e o plano e as seções sem busca o leem.
- Resultado: 4.690 palavras, 19 páginas, 17 tabelas. Ver "A confirmar", item 1.

### 5. `apostila.docx` menor

- A especificação nova está em `resumo/apostila.py`:
  - plano em 2 a 4 partes;
  - conteúdo com alvo de 8.500 palavras somadas (um terço das 25.379 da rodada 1), dividido entre as partes;
  - notas de verificação limitadas a 6 por aula (6 ÷ número de partes em cada parte), só quando a literatura contradiz ou muda o entendimento;
  - resumo executivo de até 250 palavras;
  - 15 a 20 pontos enfatizados;
  - glossário de 50 a 70 termos centrais, com definição a partir do que a aula disse;
  - dúvidas em aberto em tabela, no máximo 15;
  - 15 questões com gabarito comentado;
  - 10 itens de material complementar com link retornado pela busca;
  - sem anexo.
- Busca web só nas partes do conteúdo (notas de verificação) e no material complementar. O plano e as outras seções não recebem a ferramenta.
- O mecanismo de cache por seção, a assinatura do contexto e o filtro de links são os da rodada 1, agora em `resumo/material.py` (classe `Geracao`) e compartilhados com o resumo.
- Resultado da aula 1:

| Item | Pedido | Saiu |
|---|---|---|
| Partes do plano | 2 a 4 | 4 (organização e epiderme; derme, folículo, glândulas e barreira; lesões I; lesões II) |
| Conteúdo | ~8.500 palavras | 10.848 palavras (43% da rodada 1) |
| Notas de verificação | até 6 | 4 (uma por parte; ex.: vitamina D cutânea em cão e gato) |
| Resumo executivo | até 250 palavras | 269 |
| Pontos enfatizados | 15 a 20 | 20 |
| Glossário | 50 a 70 termos | 69 |
| Dúvidas em aberto | até 15 | 14 |
| Questões | 15 | 15, com gabarito |
| Material complementar | 10 com link verificado | 10; nenhum link descartado pelo filtro |
| Páginas | — | 62 (contra 258 da rodada 1) |

### 6. Código

- Novos: `resumo/material.py` (base comum: capa, transcrição integral, `Geracao`, filtro de links e de títulos), `resumo/resumo.py` e `resumo/referencia.docx`.
- `resumo/apostila.py` foi reescrito com a especificação nova. Saíram o anexo de transcrição, a classe `Apostila` e `TITULOS_NIVEL_1`.
- `resumo/claude.py`: o parâmetro `esforco` saiu, e todas as chamadas usam a constante `ESFORCO = "high"`. O `xhigh` não existe mais no código.
- `run.py`: Etapa 4 (transcrição), Etapa 5 (resumo) e Etapa 6 (apostila). Cada material grava `.md` e `.docx`, e a conferência vai para `manifesto.json` em `word.<material>`.
- **Ajuste de custo feito depois da execução:** o manifesto mostrou que as partes 1, 2 e 3 gravaram, cada uma, o mesmo cache de 85 mil tokens (US$ 0,68 cada). Com a busca ligada o prefixo é outro, porque as ferramentas vêm antes do `system`, e as três rodaram em paralelo. Agora a primeira chamada com busca roda junto com as seções sem busca, e as demais com busca só saem depois dela. Isso economiza cerca de US$ 1,37 por aula. Foi verificado só pelo cache: a nova ordem gera o mesmo Markdown, byte a byte, a custo zero. Ainda não rodou com chamadas reais.
- Varredura de importações e definições sem uso: nenhuma. `pytest`: 2 testes passam, e nenhum teste novo foi criado.

## Custo real por chamada (Opus 5.5, esforço `high`)

| Chamada | Entrada | Saída | Escrita de cache 1 h | Leitura de cache | Buscas | US$ |
|---|---|---|---|---|---|---|
| resumo | 503 | 23.793 | 79.467 | 0 | 0 | 1,1136 |
| apostila: 00-plano | 258 | 16.635 | 0 | 79.467 | 0 | 0,3496 |
| apostila: conteudo-parte-01 | 9.319 | 10.825 | 85.341 | 181.043 | 1 | 0,9827 |
| apostila: conteudo-parte-02 | 9.334 | 12.269 | 85.341 | 277.266 | 2 | 1,0409 |
| apostila: conteudo-parte-03 | 9.346 | 12.197 | 85.341 | 181.172 | 3 | 1,0303 |
| apostila: conteudo-parte-04 | 9.327 | 10.740 | 0 | 266.379 | 2 | 0,3254 |
| apostila: resumo-executivo | 118 | 1.225 | 0 | 79.467 | 0 | 0,0409 |
| apostila: pontos-enfatizados | 190 | 7.525 | 0 | 79.467 | 0 | 0,1672 |
| apostila: glossario | 190 | 17.878 | 0 | 79.467 | 0 | 0,3742 |
| apostila: duvidas-em-aberto | 220 | 5.241 | 0 | 79.467 | 0 | 0,1216 |
| apostila: questoes-de-revisao | 258 | 22.307 | 0 | 79.467 | 0 | 0,4631 |
| apostila: material-complementar | 324 | 6.882 | 0 | 534.526 | 20 | 0,4458 |
| **Total da rodada** | | | | | | **6,4553** |

- Resumo: US$ 1,11. Apostila: US$ 5,34, contra US$ 18,74 na rodada 1 com `xhigh` e 7 partes.
- AssemblyAI e limpeza: US$ 0 nesta rodada.
- Custo acumulado da aula no manifesto: US$ 30,05.
- A remontagem da completa e as reconversões não fizeram nenhuma chamada.

## A confirmar

1. **O resumo saiu com 19 páginas, quase o dobro do alvo de ~10.** O texto tem 4.690 palavras, contra o alvo de 3.000 a 3.500 do pedido ao modelo, e o formato em tópicos e tabelas rende cerca de 250 palavras por página. Eu tinha calibrado em 315, a densidade da apostila completa, que é texto corrido. Para chegar a ~10 páginas, o alvo teria de ser cerca de 2.300 a 2.500 palavras. Duas opções:
   - a aluna diz se 19 páginas ainda dá para "revisar numa sentada";
   - ou eu regero o resumo com o alvo menor, apagando `secoes/resumo.md`: cerca de US$ 1,10.
2. **Conteúdo da apostila com 43% do volume da rodada 1, e não um terço.** No total, a apostila tem 62 páginas, 24% das 258 da rodada 1. Se ela ainda achar grande, dá para baixar o alvo e regerar as 4 partes: cerca de US$ 3,40, já com a economia de cache.
3. **Resumo sem tempos de áudio** (Áudio N, hh:mm:ss), para leitura corrida. O pedido não falava disso; a apostila e a transcrição continuam com os tempos.
4. **Sumário só na apostila.** O resumo e a transcrição saem sem sumário; a navegação é pelo painel de títulos do Word. Assim, o resumo não abre com uma página de sumário vazia.
5. **Dúvidas em aberto em tabela** (trecho, o que se entendeu, pergunta para o professor), mais compacta que os grupos da rodada 1.
6. **Resumo e apostila sem auditoria de fidelidade.** A rodada não teve revisores, como pedido. Conferi só os documentos no Word e uma frase do glossário (vibrissas de gatos cegos, que está no Áudio 2, 00:45:25). A rodada 1 teve auditoria completa contra as transcrições. Se quiser, faço uma do mesmo jeito, só em leitura e sem API paga.
7. **Correção das listas coladas e diagramação nova da completa** (de 258 para 239 páginas, mesmo conteúdo). Não estavam no pedido.
8. **`resumo/referencia.docx` versionado como binário.** O script que o gerou foi de uso único e não ficou no repositório. Para mudar o visual, basta editar os estilos no Word.
9. **Nova ordem das chamadas com busca** validada só pelo cache; a economia de cerca de US$ 1,37 por aula se confirma na aula 2.
