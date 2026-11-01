"""Base comum dos materiais da aula: capa, transcrição integral e chamadas ao Opus 5.5 com cache em disco."""

import hashlib
import json
import logging
import re
from pathlib import Path

import pypandoc

from resumo.audios import Audio
from resumo.claude import FERRAMENTA_BUSCA, Claude
from resumo.registro import Manifesto, hms

log = logging.getLogger(__name__)

INSTRUCOES = """Você escreve material de estudo de uma aula de pós-graduação em dermatologia veterinária, a partir da transcrição integral da aula.
Tema da aula: {aula}.

Quem vai estudar é uma médica-veterinária aluna da pós. Escreva para ela estudar e revisar para a prova: português do Brasil, linguagem técnica correta, direta, sem didatismo infantil, sem floreio e sem frases de efeito.

Regras:
- A fonte é o que o professor ensinou na aula. Não invente conteúdo, casos, números ou doses que não estejam na transcrição. Literatura só entra onde a tarefa pedir.
- Trechos duvidosos da transcrição ([inaudível] ou [?]) continuam marcados como duvidosos: termo de grafia incerta mantém o [?]; nunca corrija por palpite.
- Todo link precisa ter vindo de um resultado da busca web feita por você, no formato [texto](URL). Não escreva URLs de memória.
- Use Markdown, com tabelas Markdown sempre que houver comparação, classificação, doses, protocolos ou listas de características.
- Títulos: o título da seção já existe no documento. Não use # nem ##; use ### e #### para subdivisões, salvo quando o pedido indicar outro nível.
- Ao referenciar um trecho da aula, use o formato (Áudio N, hh:mm:ss).
- Responda somente com o conteúdo pedido, sem preâmbulo, sem comentários sobre a tarefa e sem repetir o título da seção.

Glossário de termos da área (referência de grafia):
{glossario}"""

QUEBRA_DE_PAGINA = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```'
_ITEM_DE_LISTA = re.compile(r"\s*([-*+]|\d+\.)\s")


def titulo_audio(audio: Audio) -> str:
    return f"Áudio {audio.posicao} ({audio.gravado_em:%H:%M} de gravação, {hms(audio.duracao_s)})"


def capa(aula: str, subtitulo: str, audios: list[Audio]) -> str:
    """Bloco de metadados que o pandoc transforma em capa (título, subtítulo, data e duração)."""
    return "\n".join([
        "---",
        f"title: {json.dumps(aula, ensure_ascii=False)}",
        f'subtitle: "{subtitulo} — Pós-graduação em Dermatologia Veterinária"',
        f'date: "Aula gravada em {audios[0].gravado_em:%d/%m/%Y} · duração total '
        f'{hms(sum(a.duracao_s for a in audios))} · {len(audios)} áudios"',
        "lang: pt-BR",
        'toc-title: "Sumário"',
        "---",
    ])


def transcricao_integral(aula: str, audios: list[Audio], limpas: list[Path]) -> str:
    """transcricao.md: capa e a transcrição limpa de cada áudio em sequência, montada sem API."""
    blocos = [capa(aula, "Transcrição integral limpa", audios), QUEBRA_DE_PAGINA]
    for audio, limpa in zip(audios, limpas):
        blocos += [f"# {titulo_audio(audio)}", limpa.read_text(encoding="utf-8").strip()]
    return "\n\n".join(blocos) + "\n"


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


class Geracao:
    """Chamadas pagas do resumo e da apostila: mesmo prefixo em cache e uma seção por arquivo em disco."""

    def __init__(self, claude: Claude, manifesto: Manifesto, pasta_secoes: Path, aula: str, glossario: list[str],
                 audios: list[Audio], limpas: list[Path]):
        self.claude, self.manifesto, self.aula, self.audios = claude, manifesto, aula, audios
        self.pasta_secoes = pasta_secoes
        self.pasta_secoes.mkdir(parents=True, exist_ok=True)
        self.system = [{"type": "text", "text": INSTRUCOES.format(aula=aula, glossario="\n".join(glossario))}]
        transcricao = "\n\n".join(f"## {titulo_audio(a)}\n\n{p.read_text(encoding='utf-8').strip()}"
                                  for a, p in zip(audios, limpas))
        # Prefixo idêntico em todas as chamadas do resumo e da apostila: o cache de 1 h cobre as transcrições.
        self.contexto = {"type": "text", "cache_control": {"type": "ephemeral", "ttl": "1h"},
                         "text": f"Transcrição integral limpa da aula, em ordem de gravação:\n\n<transcricao>\n"
                                 f"{transcricao}\n</transcricao>"}
        self._conferir_assinatura()

    def _conferir_assinatura(self) -> None:
        """Seções em cache só valem para as mesmas instruções e transcrições que as geraram."""
        assinatura = hashlib.sha256((self.system[0]["text"] + self.contexto["text"]).encode()).hexdigest()
        arquivo = self.pasta_secoes / "contexto.sha256"
        if arquivo.exists() and arquivo.read_text(encoding="utf-8").strip() != assinatura:
            pagas = len(list(self.pasta_secoes.glob("*.md")))
            raise RuntimeError(f"As transcrições ou as instruções mudaram desde que as {pagas} seções em "
                               f"{self.pasta_secoes} foram geradas. Apague essa pasta para regerar o resumo e a "
                               f"apostila (custa {pagas} chamadas ao Opus 5.5).")
        arquivo.write_text(assinatura, encoding="utf-8")

    def secao(self, etapa: str, nome: str, pedido: str, busca: bool) -> tuple[str, list[str]]:
        """Texto da seção como o modelo escreveu e as URLs que a busca retornou, com cache em disco."""
        arquivo = self.pasta_secoes / f"{nome}.md"
        arquivo_urls = self.pasta_secoes / f"{nome}.urls.json"
        if not arquivo.exists():
            log.info("%s: gerando %s%s", etapa, nome, " (com busca web)" if busca else "")
            resposta = self.claude.gerar(etapa, nome, self.system,
                                         [self.contexto, {"type": "text", "text": pedido}],
                                         ferramentas=[FERRAMENTA_BUSCA] if busca else None)
            arquivo_urls.write_text(json.dumps(sorted(resposta.urls_buscadas), indent=1), encoding="utf-8")
            arquivo.write_text(resposta.texto.strip() + "\n", encoding="utf-8")
            log.info("%s: %s pronta", etapa, nome)
        return arquivo.read_text(encoding="utf-8"), json.loads(arquivo_urls.read_text(encoding="utf-8"))

    def montar(self, secao: tuple[str, list[str]], nome: str, titulo: str, nivel_minimo: int) -> str:
        """Seção pronta para o documento: links não verificados removidos e títulos abaixo do título dela."""
        texto, urls = secao
        return _ajustar_titulos(_filtrar_links(texto, urls, nome, self.manifesto), titulo, nivel_minimo)
