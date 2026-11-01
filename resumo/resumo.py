"""resumo.md: revisão rápida de tudo o que o professor disse, numa chamada ao Opus 5.5 sem busca web."""

from resumo.material import Geracao, capa

# Na apostila completa da aula 1, cerca de 315 palavras por página no Word: 3.000 a 3.500 palavras dão ~10 páginas.
PEDIDO_RESUMO = """Tarefa: resumo de revisão rápida da aula inteira. Não use a busca web nesta tarefa.

O critério é: a aluna revisa a aula inteira numa sentada. Alvo de 3.000 a 3.500 palavras (cerca de 10 páginas no Word); é alvo, não regra.

Conteúdo:
- Só o que foi dito em aula, na ordem em que a aula evoluiu, consolidando os áudios como uma aula só. Nenhum tópico que o professor abordou pode faltar, nem os tratados de passagem.
- Organize por tópicos. Use # para os grandes blocos da aula, na ordem em que vieram, e ## para os tópicos dentro de cada bloco (aqui esses níveis são exigidos; o título do documento já existe).
- Cada tópico em poucas linhas: frases curtas e diretas, feitas para ler e lembrar; listas curtas quando ajudarem.
- Tabelas Markdown para doses, classificações e comparações.
- Negrito só no que o professor enfatizou como importante ou provável de cair na prova, no próprio lugar em que aparece. Não use negrito para mais nada.
- Termo de grafia duvidosa na transcrição continua marcado com [?].

Não entra: transcrição, questões, links, glossário, notas de verificação com literatura, referências de tempo dos áudios e introduções ou conclusões genéricas. Comece direto pelo primeiro bloco."""


def gerar_resumo(geracao: Geracao) -> str:
    secao = geracao.secao("resumo", "resumo", PEDIDO_RESUMO, busca=False)
    return "\n\n".join([capa(geracao.aula, "Resumo para revisão rápida", geracao.audios),
                        geracao.montar(secao, "resumo", geracao.aula, 1)]) + "\n"
