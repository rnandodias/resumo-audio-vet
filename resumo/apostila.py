"""apostila.md: apostila de estudo da aula com Opus 5.5, montada por seções; busca web só onde precisa."""

import re
from concurrent.futures import ThreadPoolExecutor

from resumo.material import QUEBRA_DE_PAGINA, Geracao, capa

# Um terço das 25.379 palavras de conteúdo da apostila completa da aula 1, grande demais para estudo semanal.
PALAVRAS_DO_CONTEUDO = 8_500
NOTAS_DE_VERIFICACAO_POR_AULA = 6

PEDIDO_PLANO = """Tarefa: plano do conteúdo da apostila. Não use a busca web nesta tarefa.

Liste todos os tópicos ensinados na aula, na ordem em que a aula evoluiu, consolidando os áudios como uma aula só (um tema retomado em outro áudio entra junto do tópico original). Agrupe os tópicos em PARTES para redação, de 2 a 4 partes de tamanho parecido em volume de conteúdo.

Formato obrigatório, sem nada antes ou depois (aqui o nível ## é exigido):
## Parte 1: <título>
- <tópico> — <subtópicos separados por ponto e vírgula> (Áudio N, hh:mm:ss)
...
## Parte 2: <título>
..."""

PEDIDO_PARTE = """Tarefa: redigir a Parte {numero} do conteúdo da apostila, "{titulo}".

Plano completo do conteúdo (para você saber o que pertence às outras partes e não repetir):
{plano}

Escreva a Parte {numero} com cerca de {palavras} palavras: todos os tópicos dela, na ordem do plano, com o que o professor ensinou. É uma apostila para estudo semanal, não a transcrição reescrita: vá direto ao conteúdo, sem repetir a mesma ideia, sem digressões e sem exemplos redundantes, mas mantenha os números, doses, raças, diferenças entre espécies, casos clínicos e observações práticas que ele deu. Use tabelas quando ajudarem a comparar ou classificar e negrito nos termos-chave.

Notas de verificação: você pode usar a busca web para conferir pontos duvidosos ou que pareçam em conflito com a literatura veterinária. Só escreva uma nota quando a literatura contradiz ou muda o entendimento do que foi dito; confirmar o que o professor disse não gera nota. No máximo {notas} nota(s) nesta parte; nenhuma é aceitável. Formato: citação Markdown iniciada por "> **Nota de verificação:**", dizendo o que a literatura indica e a fonte com link, sem substituir o que o professor disse. Fora das notas, nada de literatura.

Comece direto pelo primeiro tópico. Use ### para tópicos e #### para subtópicos (o título da parte já existe)."""

# (nome do arquivo em secoes/, título no documento, pedido, usa busca web)
SECOES = [
    ("resumo-executivo", "Resumo executivo",
     """Tarefa: resumo executivo da aula, em meia página (até 250 palavras). Não use a busca web nesta tarefa.
Dois ou três parágrafos curtos, sem subtítulos e sem lista: do que a aula tratou, a linha de raciocínio do professor e as ideias centrais que a aluna precisa dominar.""", False),
    ("pontos-enfatizados", "Pontos enfatizados pelo professor",
     """Tarefa: os 15 a 20 pontos que o professor mais enfatizou como importantes, repetiu, ou indicou que costumam cair em prova ou que são erros comuns na clínica. Não use a busca web nesta tarefa.
Lista numerada, ordenada pela importância percebida. Cada ponto: o enunciado em negrito, uma ou duas frases com o que foi dito e a referência (Áudio N, hh:mm:ss). Se o professor disse explicitamente que cai em prova, indique "**(citado como de prova)**".""", False),
    ("glossario", "Glossário",
     """Tarefa: glossário dos termos centrais da aula, de 50 a 70 termos. Não use a busca web nesta tarefa.
Escolha os termos técnicos que a aluna precisa dominar para esta aula; deixe de fora termos periféricos ou citados de passagem. Tabela Markdown com as colunas Termo e Definição, em ordem alfabética. Definições de uma linha, a partir do que o professor explicou; se ele usou o termo sem defini-lo, descreva-o apenas pelo que a aula disse sobre ele.""", False),
    ("duvidas-em-aberto", "Dúvidas em aberto",
     """Tarefa: os pontos que o áudio deixou confusos e que afetam conteúdo relevante, para a aluna checar com o professor. Não use a busca web nesta tarefa.
Inclua só o que importa para estudar: trechos [inaudível] ou [?] em conteúdo relevante, números ou doses incompletos ou ambíguos, contradições entre partes da aula e termos técnicos de grafia incerta. No máximo 15 itens. Tabela Markdown com as colunas Trecho (Áudio N, hh:mm:ss), O que se entendeu e Pergunta para o professor, uma linha curta em cada célula.""", False),
    ("questoes-de-revisao", "Questões de revisão",
     """Tarefa: 15 questões de revisão com gabarito comentado, cobrindo a aula na ordem dos tópicos. Não use a busca web nesta tarefa.
Maioria de múltipla escolha (cinco alternativas, A a E, uma correta), algumas de verdadeiro ou falso com justificativa e dois ou três casos clínicos curtos. Nível de pós-graduação, cobrando o que o professor enfatizou.
Primeiro "### Questões", com cada questão em "#### Questão N". Depois "### Gabarito comentado", com "#### Questão N" e, para cada uma, a resposta e um comentário curto explicando por que ela está correta e as outras não, com a referência (Áudio N, hh:mm:ss).""", False),
    ("material-complementar", "Material complementar",
     """Tarefa: material complementar sobre os temas centrais da aula. Use a busca web.
Busque fontes veterinárias de referência: livros-texto de dermatologia veterinária (página da editora ou do livro), artigos de revisão e consensos (por exemplo, Veterinary Dermatology, WAVD, ICADA, ISCAID, ESVD/ACVD), páginas de manuais veterinários confiáveis (por exemplo, MSD Veterinary Manual) e material de universidades.
Selecione os 10 itens mais úteis para esta aula, agrupados por tipo (### Livros, ### Artigos, revisões e consensos, ### Páginas e guias). Cada item em uma linha de lista: [Título](URL) — uma linha dizendo por que vale a leitura para esta aula.
Use somente URLs que apareceram nos resultados da sua busca. Não inclua item sem link verificado.""", True),
]


def gerar_apostila(geracao: Geracao) -> str:
    plano, _ = geracao.secao("apostila", "00-plano", PEDIDO_PLANO, busca=False)
    partes = re.findall(r"^## Parte (\d+): (.+)$", plano, flags=re.MULTILINE)
    if not partes:
        raise RuntimeError("O plano da apostila veio sem partes no formato '## Parte N: título'.")
    notas = max(1, NOTAS_DE_VERIFICACAO_POR_AULA // len(partes))
    palavras = PALAVRAS_DO_CONTEUDO // len(partes)
    pedidos = {f"conteudo-parte-{int(n):02d}": (PEDIDO_PARTE.format(numero=n, titulo=t, plano=plano, notas=notas,
                                                                     palavras=palavras), True)
               for n, t in partes}
    pedidos |= {nome: (pedido, busca) for nome, _, pedido, busca in SECOES}
    # Com a busca ligada o prefixo em cache é outro (as ferramentas vêm antes do system): a primeira chamada com
    # busca grava esse cache sozinha, junto com as seções sem busca, e as demais com busca saem depois e o leem.
    primeira, *demais = [nome for nome, (_, busca) in pedidos.items() if busca]
    with ThreadPoolExecutor(max_workers=4) as executor:
        def enviar(nomes):
            return {nome: executor.submit(geracao.secao, "apostila", nome, *pedidos[nome]) for nome in nomes}

        futuros = enviar([primeira, *(nome for nome, (_, busca) in pedidos.items() if not busca)])
        futuros[primeira].result()
        futuros |= enviar(demais)
        secoes = {nome: futuro.result() for nome, futuro in futuros.items()}

    blocos = [capa(geracao.aula, "Apostila de estudo", geracao.audios), QUEBRA_DE_PAGINA,
              "# Resumo executivo",
              geracao.montar(secoes["resumo-executivo"], "resumo-executivo", "Resumo executivo", 2),
              "# Conteúdo da aula"]
    for n, titulo in partes:
        nome = f"conteudo-parte-{int(n):02d}"
        blocos += [f"## {titulo}", geracao.montar(secoes[nome], nome, titulo, 3)]
    for nome, titulo, _, _ in SECOES[1:]:
        blocos += [f"# {titulo}", geracao.montar(secoes[nome], nome, titulo, 2)]
    return "\n\n".join(blocos) + "\n"
