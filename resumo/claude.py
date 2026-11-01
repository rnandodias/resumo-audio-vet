"""Chamadas ao Opus 5.5 com streaming, continuação de pause_turn e registro de consumo."""

import logging
from dataclasses import dataclass, field

import anthropic

from resumo.registro import Manifesto

log = logging.getLogger(__name__)

MODELO = "claude-opus-5-5"
MAX_TOKENS = 128_000
FERRAMENTA_BUSCA = {"type": "web_search_20260209", "name": "web_search", "max_uses": 20}
MAX_CONTINUACOES = 10


@dataclass
class Resposta:
    texto: str
    urls_buscadas: set[str] = field(default_factory=set)


def _somar(uso: dict, usage) -> None:
    criacao = usage.cache_creation
    uso["entrada"] += usage.input_tokens
    uso["saida"] += usage.output_tokens
    uso["cache_escrita_5m"] += criacao.ephemeral_5m_input_tokens if criacao else usage.cache_creation_input_tokens or 0
    uso["cache_escrita_1h"] += criacao.ephemeral_1h_input_tokens if criacao else 0
    uso["cache_leitura"] += usage.cache_read_input_tokens or 0
    uso["buscas_web"] += usage.server_tool_use.web_search_requests if usage.server_tool_use else 0


class Claude:
    def __init__(self, manifesto: Manifesto):
        self.cliente = anthropic.Anthropic(max_retries=6)
        self.manifesto = manifesto

    def gerar(self, etapa: str, referencia: str, system: list[dict], conteudo, ferramentas: list[dict] | None = None,
              esforco: str = "high") -> Resposta:
        mensagens = [{"role": "user", "content": conteudo}]
        extras = {"tools": ferramentas} if ferramentas else {}
        textos, urls = [], set()
        for continuacao in range(MAX_CONTINUACOES):
            with self.cliente.messages.stream(model=MODELO, max_tokens=MAX_TOKENS, system=system, messages=mensagens,
                                              thinking={"type": "adaptive"}, output_config={"effort": esforco},
                                              **extras) as stream:
                mensagem = stream.get_final_message()
            # Cada chamada é registrada assim que termina: se uma continuação falhar, o que já foi pago fica no manifesto.
            uso = dict.fromkeys(("entrada", "saida", "cache_escrita_5m", "cache_escrita_1h", "cache_leitura",
                                 "buscas_web"), 0)
            _somar(uso, mensagem.usage)
            self.manifesto.registrar_anthropic(etapa, f"{referencia} (continuação {continuacao})" if continuacao
                                               else referencia, uso)
            log.debug("%s/%s: %s, stop_reason=%s", etapa, referencia, uso, mensagem.stop_reason)
            for bloco in mensagem.content:
                if bloco.type == "text":
                    textos.append(bloco.text)
                    urls.update(c.url for c in bloco.citations or [] if c.type == "web_search_result_location")
                elif bloco.type == "web_search_tool_result" and isinstance(bloco.content, list):
                    urls.update(resultado.url for resultado in bloco.content)
            if mensagem.stop_reason != "pause_turn":
                break
            # A busca web pausou o turno no servidor: reenviar o conteúdo como está retoma de onde parou.
            mensagens.append({"role": "assistant", "content": mensagem.content})
        if mensagem.stop_reason != "end_turn":
            detalhe = mensagem.stop_details if mensagem.stop_reason == "refusal" else ""
            raise RuntimeError(f"{etapa}/{referencia}: resposta incompleta do {MODELO} "
                               f"(stop_reason={mensagem.stop_reason} {detalhe}). Nada foi salvo.")
        return Resposta("".join(textos), urls)
