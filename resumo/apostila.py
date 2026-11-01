"""Etapa 4: apostila da aula com Opus 5.5 e busca web, montada por seções."""

import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pypandoc

from resumo.audios import Audio
from resumo.claude import FERRAMENTA_BUSCA, Claude
from resumo.registro import Manifesto, hms

log = logging.getLogger(__name__)

INSTRUCOES = """Você escreve a apostila de estudo de uma aula de pós-graduação em dermatologia veterinária, a partir da transcrição integral da aula.
Tema da aula: {aula}.

Quem vai estudar é uma médica-veterinária aluna da pós. Escreva para ela estudar e revisar para a prova: português do Brasil, linguagem técnica correta, direta, sem didatismo infantil, sem floreio e sem frases de efeito.

Regras:
- A fonte principal é o que o professor ensinou na aula. Não invente conteúdo, casos, números ou doses que não estejam na transcrição.
- Quando a transcrição estiver duvidosa (marcada com [inaudível] ou [?]) ou quando algo dito parecer em conflito com a literatura veterinária, você pode usar a busca web para conferir. Nesse caso, mantenha o que o professor disse e acrescente uma nota curta em citação Markdown iniciada por "> **Nota de verificação:**", dizendo o que a literatura indica e a fonte com link. Nunca substitua silenciosamente o que foi dito.
- Todo link precisa ter vindo de um resultado da busca web feita por você, no formato [texto](URL). Não escreva URLs de memória.
- Use Markdown: listas, negrito para termos-chave e tabelas Markdown sempre que houver comparação, classificação, doses, protocolos ou listas de características.
- Títulos: o título da seção já existe no documento. Não use # nem ##; use ### e #### para subdivisões, salvo quando o pedido indicar outro nível.
- Ao referenciar um trecho da aula, use o formato (Áudio N, hh:mm:ss).
- Responda somente com o conteúdo pedido, sem preâmbulo, sem comentários sobre a tarefa e sem repetir o título da seção.

Glossário de termos da área (referência de grafia):
{glossario}"""

PEDIDO_PLANO = """Tarefa: plano do conteúdo da apostila. Não use a busca web nesta tarefa.

Liste todos os tópicos ensinados na aula, na ordem em que a aula evoluiu, consolidando os áudios como uma aula só (um tema retomado em outro áudio entra junto do tópico original). Agrupe os tópicos em PARTES para redação, de 3 a 7 partes de tamanho parecido em volume de conteúdo.

Formato obrigatório, sem nada antes ou depois (aqui o nível ## é exigido):
## Parte 1: <título>
- <tópico> — <subtópicos separados por ponto e vírgula> (Áudio N, hh:mm:ss)
...
## Parte 2: <título>
..."""

PEDIDO_PARTE = """Tarefa: redigir a Parte {numero} do conteúdo da apostila, "{titulo}".

Plano completo do conteúdo (para você saber o que pertence às outras partes e não repetir):
{plano}

Escreva a Parte {numero} completa: tudo o que o professor ensinou sobre esses tópicos, sem omitir detalhes, exemplos, casos clínicos, números, doses, protocolos, diferenças entre espécies e raças, e observações práticas. Consolide o que foi dito em áudios diferentes. Não é resumo: é o material de estudo completo desses tópicos. Use tabelas sempre que couber.
Comece direto pelo primeiro tópico. Use ### para tópicos e #### para subtópicos (o título da parte já existe)."""

SECOES = [
    ("resumo-executivo", "Resumo executivo",
     """Tarefa: resumo executivo da aula. Não use a busca web nesta tarefa.
Em até uma página: do que a aula tratou, a linha de raciocínio do professor e as ideias centrais que a aluna precisa dominar. Parágrafos curtos, sem subtítulos; uma lista ao final com os 5 a 10 conceitos centrais."""),
    ("pontos-enfatizados", "Pontos enfatizados pelo professor",
     """Tarefa: listar os pontos que o professor enfatizou como importantes, repetiu, ou indicou que costumam cair em prova ou que são erros comuns na clínica. Não use a busca web nesta tarefa.
Para cada ponto: o enunciado do ponto em negrito, uma explicação curta do que foi dito e a referência (Áudio N, hh:mm:ss). Se o professor disse explicitamente que cai em prova, indique "**(citado como de prova)**". Ordene pela importância percebida."""),
    ("glossario", "Glossário",
     """Tarefa: glossário dos termos técnicos usados na aula. Não use a busca web nesta tarefa, exceto para confirmar uma definição duvidosa.
Tabela Markdown com as colunas Termo e Definição, em ordem alfabética. Definições técnicas e curtas, coerentes com o que o professor explicou; quando o professor deu uma definição própria, use a dele. Inclua todos os termos técnicos relevantes que apareceram."""),
    ("duvidas-em-aberto", "Dúvidas em aberto",
     """Tarefa: listar os pontos que o áudio deixou confusos para a aluna checar com o professor. Não use a busca web nesta tarefa.
Inclua: trechos marcados [inaudível] ou [?] que afetam conteúdo relevante, números ou doses incompletos ou ambíguos, afirmações que se contradizem entre partes da aula, termos de grafia incerta, e perguntas de alunos que ficaram sem resposta clara.
Para cada item: (Áudio N, hh:mm:ss), o que se entendeu, por que está em dúvida e a pergunta sugerida para levar ao professor. Agrupe por tipo de problema, com ### para cada grupo."""),
    ("questoes-de-revisao", "Questões de revisão",
     """Tarefa: questões de revisão com gabarito comentado, cobrindo toda a aula na ordem dos tópicos. Não use a busca web nesta tarefa.
Faça de 25 a 35 questões: maioria de múltipla escolha (cinco alternativas, A a E, uma correta), algumas de verdadeiro ou falso com justificativa e algumas discursivas curtas, incluindo casos clínicos curtos. Nível de pós-graduação, cobrando o que o professor enfatizou.
Primeiro "### Questões", com cada questão em "#### Questão N". Depois "### Gabarito comentado", com "#### Questão N" e, para cada uma, a resposta e o comentário explicando por que ela está correta e por que as outras não estão, com a referência (Áudio N, hh:mm:ss)."""),
    ("material-complementar", "Material complementar",
     """Tarefa: material complementar sobre os temas da aula. Use a busca web.
Busque fontes veterinárias de referência sobre os temas centrais da aula: livros-texto de referência em dermatologia veterinária (página da editora ou do livro), artigos de revisão e consensos (por exemplo, publicações de periódicos como Veterinary Dermatology, documentos da WAVD, ICADA, ISCAID, ESVD/ACVD), capítulos ou páginas de manuais veterinários confiáveis (por exemplo, MSD Veterinary Manual) e material de universidades.
Selecione de 12 a 25 itens realmente úteis para os temas desta aula, agrupados por tipo (### Livros, ### Artigos, revisões e consensos, ### Páginas e guias). Cada item em uma linha de lista: [Título](URL) — uma linha dizendo por que vale a leitura para esta aula.
Use somente URLs que apareceram nos resultados da sua busca. Não inclua item sem link verificado."""),
]

TITULO_ANEXO = "Anexo — Transcrição integral limpa"
TITULOS_NIVEL_1 = ["Resumo executivo", "Conteúdo da aula", *(titulo for _, titulo, _ in SECOES[1:]), TITULO_ANEXO]

_ITEM_DE_LISTA = re.compile(r"\s*([-*+]|\d+\.)\s")
_QUEBRA_DE_PAGINA = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```'


def _normalizar(url: str) -> str:
    return url.split("#")[0].rstrip("/").lower()


def _links(texto: str) -> list[str]:
    """URLs de todos os links do Markdown (inline, autolink, referência), lidas pelo AST do pandoc."""
    urls = []

    def percorrer(no):
        if isinstance(no, dict):
            if no.get("t") == "Link":
                urls.append(no["c"][2][0])
            percorrer(no.get("c"))
        elif isinstance(no, list):
            for filho in no:
                percorrer(filho)

    percorrer(json.loads(pypandoc.convert_text(texto, "json", format="markdown"))["blocks"])
    return urls


def _filtrar_links(texto: str, urls_buscadas: list[str], secao: str, manifesto: Manifesto) -> str:
    """Tira links que não vieram da busca web; no material complementar, tira o item inteiro."""
    verificadas = {_normalizar(u) for u in urls_buscadas}

    def avisar(motivo: str) -> None:
        manifesto.registrar_aviso(f"{secao}: {motivo}")
        log.warning("%s: %s", secao, motivo)

    if secao == "material-complementar":
        linhas = []
        for linha in texto.splitlines():
            if _ITEM_DE_LISTA.match(linha):
                urls = _links(linha)
                if not urls or any(_normalizar(u) not in verificadas for u in urls):
                    avisar(f"item removido (link ausente ou não retornado pela busca): {linha.strip()}")
                    continue
            linhas.append(linha)
        texto = "\n".join(linhas)
    for url in {u for u in _links(texto) if _normalizar(u) not in verificadas}:
        avisar(f"link não retornado pela busca removido: {url}")
        texto = re.sub(r"\[([^\]]*)\]\(<?" + re.escape(url) + r">?(?:\s+\"[^\"]*\")?\)", r"\1", texto)
        texto = texto.replace(f"<{url}>", url)
    restantes = [u for u in _links(texto) if _normalizar(u) not in verificadas]
    if restantes:
        raise RuntimeError(f"{secao}: links não verificados que o filtro não conseguiu remover: {restantes}")
    return texto


def _ajustar_titulos(texto: str, titulo: str, nivel_minimo: int) -> str:
    """Garante que os títulos do modelo fiquem abaixo do título da seção e não o repitam."""
    linhas = texto.splitlines()
    if linhas and linhas[0].lstrip("#").strip().lower() == titulo.lower():
        linhas = linhas[1:]
    em_codigo, niveis = False, []
    for linha in linhas:
        em_codigo ^= linha.startswith("```")
        if not em_codigo and (m := re.match(r"(#{1,6}) ", linha)):
            niveis.append(len(m.group(1)))
    deslocamento = max(0, nivel_minimo - min(niveis, default=nivel_minimo))
    if deslocamento:
        em_codigo = False
        for i, linha in enumerate(linhas):
            em_codigo ^= linha.startswith("```")
            if not em_codigo and re.match(r"#{1,6} ", linha):
                linhas[i] = "#" * min(6, linha.index(" ") + deslocamento) + linha[linha.index(" "):]
    return "\n".join(linhas).strip()


def _titulo_audio(audio: Audio) -> str:
    return f"Áudio {audio.posicao} ({audio.gravado_em:%H:%M} de gravação, {hms(audio.duracao_s)})"


class Apostila:
    def __init__(self, claude: Claude, manifesto: Manifesto, pasta: Path, aula: str, glossario: list[str],
                 audios: list[Audio], limpas: list[Path]):
        self.claude, self.manifesto, self.aula = claude, manifesto, aula
        self.pasta_secoes = pasta / "secoes"
        self.pasta_secoes.mkdir(parents=True, exist_ok=True)
        self.audios = audios
        self.limpas = {a.posicao: p.read_text(encoding="utf-8").strip() for a, p in zip(audios, limpas)}
        self.system = [{"type": "text", "text": INSTRUCOES.format(aula=aula, glossario="\n".join(glossario))}]
        transcricao = "\n\n".join(f"## {_titulo_audio(a)}\n\n{self.limpas[a.posicao]}" for a in audios)
        # Prefixo idêntico em todas as chamadas da etapa: o cache de 1 h cobre as transcrições inteiras.
        self.contexto = {"type": "text", "cache_control": {"type": "ephemeral", "ttl": "1h"},
                         "text": f"Transcrição integral limpa da aula, em ordem de gravação:\n\n<transcricao>\n"
                                 f"{transcricao}\n</transcricao>"}

    def _conferir_assinatura(self) -> None:
        """Seções em cache só valem para as mesmas instruções e transcrições que as geraram."""
        assinatura = hashlib.sha256((self.system[0]["text"] + self.contexto["text"]).encode()).hexdigest()
        arquivo = self.pasta_secoes / "contexto.sha256"
        if arquivo.exists() and arquivo.read_text(encoding="utf-8").strip() != assinatura:
            pagas = len(list(self.pasta_secoes.glob("*.md")))
            raise RuntimeError(f"As transcrições ou as instruções mudaram desde que as {pagas} seções em "
                               f"{self.pasta_secoes} foram geradas. Apague essa pasta para regerar a apostila "
                               f"(custa {pagas} chamadas ao Opus 5.5).")
        arquivo.write_text(assinatura, encoding="utf-8")

    def _secao(self, nome: str, pedido: str) -> tuple[str, list[str]]:
        """Texto da seção como o modelo escreveu e as URLs que a busca retornou, com cache em disco."""
        arquivo = self.pasta_secoes / f"{nome}.md"
        arquivo_urls = self.pasta_secoes / f"{nome}.urls.json"
        if not arquivo.exists():
            log.info("Apostila: gerando %s", nome)
            resposta = self.claude.gerar("apostila", nome, self.system,
                                         [self.contexto, {"type": "text", "text": pedido}],
                                         ferramentas=[FERRAMENTA_BUSCA], esforco="xhigh")
            arquivo_urls.write_text(json.dumps(sorted(resposta.urls_buscadas), indent=1), encoding="utf-8")
            arquivo.write_text(resposta.texto.strip() + "\n", encoding="utf-8")
            log.info("Apostila: %s pronta", nome)
        else:
            log.info("Apostila: seção %s em cache", nome)
        return arquivo.read_text(encoding="utf-8"), json.loads(arquivo_urls.read_text(encoding="utf-8"))

    def gerar(self) -> str:
        self._conferir_assinatura()
        plano, _ = self._secao("00-plano", PEDIDO_PLANO)
        partes = re.findall(r"^## Parte (\d+): (.+)$", plano, flags=re.MULTILINE)
        if not partes:
            raise RuntimeError("O plano da apostila veio sem partes no formato '## Parte N: título'.")
        pedidos = {f"conteudo-parte-{int(n):02d}": PEDIDO_PARTE.format(numero=n, titulo=t, plano=plano)
                   for n, t in partes}
        pedidos |= {nome: pedido for nome, _, pedido in SECOES}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futuros = {nome: executor.submit(self._secao, nome, pedido) for nome, pedido in pedidos.items()}
            secoes = {nome: futuro.result() for nome, futuro in futuros.items()}
        return self._montar(partes, secoes)

    def _texto(self, secoes: dict, nome: str, titulo: str, nivel_minimo: int) -> str:
        texto, urls = secoes[nome]
        return _ajustar_titulos(_filtrar_links(texto, urls, nome, self.manifesto), titulo, nivel_minimo)

    def _montar(self, partes: list[tuple[str, str]], secoes: dict) -> str:
        total = sum(a.duracao_s for a in self.audios)
        capa = "\n".join([
            "---",
            f"title: {json.dumps(self.aula, ensure_ascii=False)}",
            'subtitle: "Apostila de estudo — Pós-graduação em Dermatologia Veterinária"',
            f'date: "Aula gravada em {self.audios[0].gravado_em:%d/%m/%Y} · duração total {hms(total)} · '
            f'{len(self.audios)} áudios"',
            "lang: pt-BR",
            'toc-title: "Sumário"',
            "---",
        ])
        blocos = [capa, _QUEBRA_DE_PAGINA,
                  "# Resumo executivo", self._texto(secoes, "resumo-executivo", "Resumo executivo", 2),
                  "# Conteúdo da aula"]
        for n, titulo in partes:
            blocos += [f"## {titulo}", self._texto(secoes, f"conteudo-parte-{int(n):02d}", titulo, 3)]
        for nome, titulo, _ in SECOES[1:]:
            blocos += [f"# {titulo}", self._texto(secoes, nome, titulo, 2)]
        blocos.append(f"# {TITULO_ANEXO}")
        for audio in self.audios:
            blocos += [f"## {_titulo_audio(audio)}", self.limpas[audio.posicao]]
        return "\n\n".join(blocos) + "\n"
