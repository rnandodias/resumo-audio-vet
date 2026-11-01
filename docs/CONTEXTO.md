# Contexto e decisões

Registro das decisões do projeto e do que vem a seguir. Atualizado ao fim de cada rodada.

## Decisões

| Data | Decisão | Motivo |
|---|---|---|
| 01/11/2026 | **AssemblyAI** para transcrição, modelo `universal-3-5-pro` (o mais preciso da API assíncrona; o `universal-3-pro` foi descontinuado), português, keyterms e diarização | Precisão em áudio ruidoso em português, gravado por celular a distância do professor. Keyterms (até 1.000 palavras) e `prompt` são mutuamente exclusivos nesse modelo; escolhemos keyterms, que ataca diretamente os termos técnicos |
| 01/11/2026 | **Uma apostila por aula**, não por áudio | A aula é uma unidade; os áudios são cortes arbitrários da gravação. A apostila consolida os áudios como uma aula só |
| 01/11/2026 | **Ordem pela data de gravação** (`creation_time` do arquivo) | O nome dos arquivos do WhatsApp é a hora da exportação e não serve para ordenar |
| 01/11/2026 | **Deduplicação pelo hash do stream de áudio**, não do arquivo | A duplicata conhecida da aula 1 difere em 6 bytes de metadados do MP4; o áudio é idêntico |
| 01/11/2026 | **Estrutura da apostila**: capa; resumo executivo; conteúdo por tópicos na ordem da aula; pontos enfatizados/prova; glossário; dúvidas em aberto; questões com gabarito comentado; material complementar (só links retornados pela busca); anexo com a transcrição integral limpa por áudio | Aprovada pelo usuário antes da rodada 01 |
| 01/11/2026 | **Opus 5.5** (`claude-opus-5-5`) na limpeza e na apostila, `max_tokens` 128000, busca web nativa na apostila | Qualidade primeiro |
| 01/11/2026 | Limpeza: **uma chamada por áudio**, sem divisão em blocos; erro explícito se um áudio passar de 14 mil palavras brutas | Medido na aula 1: o maior áudio (48 min, 5.918 palavras) gastou no máximo ~40 mil tokens de saída (texto + raciocínio, até ~7 por palavra), bem abaixo dos 128 mil. 14 mil palavras (~2 h de fala) é o teto seguro; divisão em blocos seria código sem uso com áudios do WhatsApp |
| 01/11/2026 | Apostila **gerada por seções** com prefixo comum em cache | Cada parte do conteúdo tem a saída inteira do modelo à disposição; nenhuma seção fica rasa ou truncada |
| 01/11/2026 | Word via **pandoc empacotado no venv** (`pypandoc_binary`) | Pandoc não estava instalado no sistema; o pacote evita instalar software global e dá títulos navegáveis, sumário, tabelas e links reais |
| 01/11/2026 | **Aplicação web na VPS fica para depois** | Primeiro validar a apostila; só então construir app, banco e telas |

## O que vem a seguir

1. Aprovação da apostila da aula 1 pela aluna (conteúdo, profundidade, formato do Word). Ajustes de prompt entram antes da aula 2.
2. Itens da lista "a confirmar" em `docs/rodadas/rodada-01.md`.
3. Próximas aulas: colocar os áudios em `input/` e rodar com o nome da aula; ampliar o glossário com os termos novos.
4. Depois da aprovação: aplicação web na VPS (upload dos áudios, fila de processamento, histórico de apostilas).
