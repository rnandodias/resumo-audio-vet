# Rodada 01: pipeline de áudio da aula até a apostila em Word

**Data:** 01/11/2026 · **Modelo:** Opus 5.5 · **Aula processada:** Anatomia Dermatológica (gravada em 23/10/2026)

## Resultado

O pipeline roda de ponta a ponta com `python run.py --aula "Anatomia Dermatológica"`. Ele gerou:

- `output/anatomia-dermatologica/apostila.docx`: 258 páginas no Word, com capa, sumário, 297 títulos navegáveis, 109 tabelas e 127 links clicáveis.
- `output/anatomia-dermatologica/apostila.md`: a mesma apostila em Markdown.
- `output/anatomia-dermatologica/manifesto.json`: áudios em ordem, hashes, duplicata, consumo e custo de cada chamada.
- `output/anatomia-dermatologica/transcricoes/`: 8 transcrições brutas (`.bruta.md`) e 8 limpas (`.limpa.md`).
- `output/anatomia-dermatologica/secoes/`: cache das 15 seções geradas.

Uma segunda execução sai inteira do cache, custa zero e produz o mesmo resultado (verificado).

## O que foi feito

### Etapa 1: ordenar e deduplicar

- Os 9 arquivos de `input/` foram ordenados pelo `creation_time` do MP4: 09:27, 10:35, 11:24, 13:34, 14:49, 15:35, 16:08 e 16:15 no horário de Brasília. Nenhum arquivo precisou usar a data de modificação como alternativa.
- **Achado:** a duplicata conhecida (`15.43.01 (1).mp4` e `15.43.01.mp4`) tem **SHA-256 diferente no arquivo inteiro**. São 6 bytes diferentes nos carimbos de tempo do átomo de metadados do MP4. Um hash do arquivo não pegaria essa duplicata. Por isso o hash é calculado sobre os pacotes do stream de áudio (`ffmpeg -map 0:a -c copy -f hash -hash sha256`), e aí as duas cópias batem. Ficou a cópia sem o sufixo " (1)".
- Resultado: 8 áudios únicos com 3:40:32 no total, exatamente o esperado.
- A extração gera FLAC mono a 16 kHz, gravado primeiro num arquivo provisório. Assim, uma extração interrompida nunca vira cache.

### Etapa 2: transcrição (AssemblyAI)

- Modelo **`universal-3-5-pro`**. A documentação atual (consultada em 01/11/2026) mostra que o `universal-3-pro` foi descontinuado e substituído por ele. Configuração: `language_code="pt"`, diarização com 2 a 8 falantes e 451 keyterms (o nome da aula mais o glossário).
- Keyterms: o limite da API é de 1.000 **palavras somadas**, com até 6 palavras por termo. O glossário tem 450 termos e 737 palavras. Se passar do limite, o código para com erro em vez de cortar sem avisar. Neste modelo, `keyterms_prompt` e `prompt` não podem ser usados juntos, e escolhi keyterms.
- O SDK oficial (1.8.2) ainda não tem o modelo novo no enum da resposta e falha ao ler o transcript. Por isso o SDK monta a configuração e faz o upload, enquanto o envio e o polling usam o cliente HTTP autenticado do próprio SDK. O cache guarda o JSON bruto completo, transcript e parágrafos.
- O cache é localizado pelo hash. Se a posição do áudio mudar, os arquivos são renomeados. O id do job fica salvo em `.pendente` logo depois do envio, para que uma rodada interrompida retome o mesmo job sem pagar de novo.
- Os 8 áudios foram transcritos em paralelo em cerca de 6 minutos.

### Etapa 3: limpeza (Opus 5.5)

- Uma chamada por áudio, com `max_tokens` de 128.000, thinking adaptativo e esforço `high`. O system prompt (instruções e glossário) fica em cache.
- Proporção de palavras limpas sobre brutas por áudio: 94%, 92%, 95%, 95%, 93%, 95%, 89% e 93%. Nenhum áudio chegou perto do limite de 30% de encolhimento.
- A limpeza juntou o professor que a diarização tinha dividido em dois falantes e marcou 40 perguntas de alunos.

### Etapa 4: apostila (Opus 5.5 com busca web)

- O prefixo é o mesmo em todas as chamadas: instruções, glossário e as 8 transcrições limpas, num cache de 1 h. Foram 12,8 milhões de tokens lidos do cache, a US$ 0,20/MTok em vez de US$ 4.
- **Plano:** 7 partes na ordem da aula:
  1. Limites e funções da pele.
  2. Camadas e queratinização.
  3. Células, derme, hipoderme e unidade folicular.
  4. Folículo, ciclo do pelo e tricograma.
  5. Glândulas, pH e tópicos.
  6. Lesões I.
  7. Lesões II e casos.
- Cada parte do conteúdo e cada seção foi uma chamada separada, 4 em paralelo, com esforço `xhigh` e a ferramenta `web_search_20260209`. O conteúdo tem 25.379 palavras e 59 "Notas de verificação", em que a literatura foi conferida sem substituir o que o professor disse.
- Seções:
  - resumo executivo;
  - pontos enfatizados;
  - glossário com cerca de 170 termos;
  - dúvidas em aberto;
  - 35 questões com gabarito comentado;
  - 25 itens de material complementar, todos com link retornado pela busca (zero links descartados);
  - anexo com a transcrição limpa por áudio.
- A capa e o anexo são montados localmente. Os links que a busca não retornou são removidos pelo código: a lista de links sai da árvore de sintaxe do pandoc, e a conferência final falha se sobrar algum.
- O Word é gerado pelo pandoc empacotado no venv e reaberto com python-docx. A conferência checa os títulos de nível 1 (exatamente os esperados, na ordem), a capa, as tabelas e os links. Também exportei o Word para PDF e conferi visualmente a capa, o sumário, as tabelas e as notas.

## Revisão e auditoria

- **Revisão do código:** foi independente, com três lentes (APIs e Word, custo e cache, aderência ao pedido) e verificação adversarial de cada achado. 7 problemas foram confirmados e corrigidos antes de gerar a apostila:
  - O front matter YAML não era lido, e a capa não saía.
  - Títulos `#` gerados pelo modelo podiam virar capítulos falsos.
  - O filtro de links deixava passar autolinks e descartava URLs com parênteses.
  - O consumo de uma chamada já paga se perdia se a continuação falhasse.
  - Um FLAC parcial podia virar cache e ser enviado pago.
  - O guarda de tamanho da limpeza estava frouxo (40 mil palavras). Foi recalibrado para 14 mil com o dado medido de até 7 tokens de saída por palavra.
  - Seções em cache eram reaproveitadas mesmo depois de as transcrições mudarem. Agora uma assinatura do contexto bloqueia isso com erro explícito.
- **Auditoria do conteúdo da apostila:** foi feita contra as transcrições, só em leitura, com verificação adversarial.
  - Fidelidade alta: números, raças, casos e listas conferem, e nenhuma dose foi inventada.
  - Cobertura completa: cerca de 250 itens técnicos levantados nas transcrições, todos presentes.
  - Gabarito correto nas 35 questões.
  - Dois deslizes de gravidade média, ainda **não corrigidos** (ver "A confirmar"):
    1. Parte 4, tabela do tricograma: "a confirmar por histopatologia" aparece como dito em aula. O professor disse "confirmar com as células [?]" (Áudio 2, 00:28:13).
    2. Pontos enfatizados, item 33: "no homem e no cavalo, em toda a pele" (glândulas écrinas). O professor citou homem e cavalo, mas não disse "em toda a pele" (Áudio 3, 00:22:04–00:22:23).
  - Fora isso, cerca de 20 problemas de gravidade baixa: pequenas generalizações, um erro de digitação na Q33 e duas definições do glossário (Tumor e Termorregulação) que vão um pouco além do que a aula disse.

## Problemas encontrados

- **OneDrive travou arquivos do venv** durante a instalação, e o venv teve de ser recriado. Pode voltar a acontecer. Ver "A confirmar".
- **Pandoc não estava instalado.** Usei o `pypandoc_binary`, que traz o pandoc dentro do venv, em vez de instalar software no sistema.
- **Chamada do plano perdida:** interrompi a primeira execução da Etapa 4 para aplicar as correções da revisão, com a chamada do plano em andamento. Ela não chegou a registrar consumo no manifesto. Estimo até cerca de US$ 2,30, pelo custo do plano refeito. A partir desta rodada, o consumo é registrado a cada chamada concluída.
- **Sumário do Word:** o pandoc grava o sumário como campo a atualizar. O Word no computador oferece atualizá-lo ao abrir. No Word para web ou celular ele pode aparecer vazio, mas o painel de navegação por títulos funciona sempre.

## Consumo e custo real

| Item | Quantidade | Custo (US$) |
|---|---|---|
| AssemblyAI (U3.5 Pro + keyterms + diarização, US$ 0,28/h) | 220,6 min | 1,03 |
| Opus 5.5: limpeza (8 chamadas) | 80.877 tokens de entrada, 170.721 de saída, 16.788 de cache | 3,83 |
| Opus 5.5: apostila (15 chamadas) | 99.808 tokens de entrada, 687.781 de saída, 12,8 M de leitura de cache, 85.438 de escrita de cache (1 h), 134 buscas web | 18,74 |
| **Total registrado no manifesto** | | **23,60** |
| Chamada do plano interrompida (não registrada, estimativa) | | até cerca de 2,30 |

A maior parte do custo vem da saída da apostila: o esforço `xhigh` gera muito raciocínio. O plano sozinho custou US$ 2,29, com 80 mil tokens de saída. O detalhe por chamada está em `manifesto.json`.

## Qualidade percebida da transcrição

| Áudio | Duração | Confiança AAI | Falantes detectados | `[inaudível]` | `[?]` | Perguntas de alunos |
|---|---|---|---|---|---|---|
| 1 (09:27) | 26:44 | 0,933 | 3 | 27 | 15 | 2 |
| 2 (10:35) | 48:37 | 0,946 | 5 | 21 | 41 | 3 |
| 3 (11:24) | 40:09 | 0,942 | 3 | 32 | 41 | 10 |
| 4 (13:34) | 10:35 | 0,916 | 2 | 8 | 25 | 0 |
| 5 (14:49) | 45:38 | 0,933 | 2 | 45 | 46 | 8 |
| 6 (15:35) | 26:00 | 0,936 | 3 | 32 | 21 | 9 |
| 7 (16:08) | 5:27 | 0,938 | 3 | 8 | 5 | 1 |
| 8 (16:15) | 17:21 | 0,913 | 2 | 4 | 27 | 7 |
| **Total** | **3:40:32** | | | **177** | **221** | **40** |

- O texto é bem compreensível, mas os termos técnicos sofrem com a distância. Exemplos: "sarna bubonéssica" (provavelmente sarcóptica), "vasculite pós-placental" (provavelmente pós-vacinal), "exames de complexidade", "telámona escama", "are loyal".
- A limpeza manteve essas palavras com `[?]` em vez de corrigir por palpite, como manda a regra de fidelidade. As dúvidas relevantes foram para a seção "Dúvidas em aberto".
- Os `[inaudível]` se concentram nos áudios 3 e 5, que têm mais discussão com a turma e falas sobrepostas.
- A diarização confunde o professor com ele mesmo (A/C) e não separa bem os alunos que falam longe do celular. A limpeza corrigiu a atribuição pelo contexto.

## A confirmar

1. **Os dois deslizes da apostila** (histopatologia na Parte 4; écrinas "em toda a pele" nos pontos enfatizados). Há duas opções: corrigir à mão as duas frases em `secoes/` e remontar, sem custo, ou regerar as duas seções, com custo de cerca de US$ 2.
2. **Divisão em blocos na limpeza não implementada.** Mantive uma chamada por áudio e um erro explícito acima de 14 mil palavras brutas (cerca de 2 h de fala). Os áudios do WhatsApp ficam bem abaixo disso. O pedido previa blocos com sobreposição.
3. **Pandoc via `pypandoc_binary`** no venv, em vez de instalar o pandoc no sistema ou usar python-docx puro.
4. **Sem fallback de recusa** (`fallbacks`) nas chamadas ao Opus 5.5, por causa da regra "um caminho só". Se o classificador de segurança recusar um trecho, a rodada para com erro claro. Isso não ocorreu nesta aula.
5. **Esforço:** `high` na limpeza e `xhigh` na apostila. Baixar a apostila para `high` deve cortar boa parte dos US$ 18,74, mas eu mediria a diferença de qualidade antes de mudar.
6. **Diarização limitada a 2–8 falantes.** O custo é o mesmo com qualquer limite. A variante "experimental" (+US$ 0,065/h) não tem parâmetro documentado na API.
7. **Keyterms em vez de `prompt`** na AssemblyAI. Os dois são exclusivos; não testei qual rende mais neste áudio.
8. **Duplicata:** fica a cópia de nome mais curto, sem o " (1)".
9. **Sumário do Word** depende de atualização ao abrir no Word para computador. Dá para entregar o sumário já preenchido, mas isso exige o Word instalado na hora de gerar, o que não serve para a VPS.
10. **Tabelas no Word** saem no estilo padrão do pandoc, sem grade. Dá para criar um documento de referência com bordas e fontes próprias, se ela preferir.
11. **Repositório na pasta do OneDrive:** a sincronização travou arquivos do `.venv`. Considerar excluir `.venv/` e `output/*/audio/` da sincronização.
12. **Seções da apostila (`secoes/*.md`) versionadas no git** junto com as URLs da busca, como cache das chamadas pagas. O pedido não dizia nada sobre elas.
