"""Etapa 3: transcrição integral limpa de cada áudio com Opus 5.5."""

import logging
import re
from pathlib import Path

from resumo.audios import Audio
from resumo.claude import Claude

log = logging.getLogger(__name__)

# Medido na aula 1: até ~7 tokens de saída (texto + raciocínio) por palavra bruta. Acima disso a resposta
# pode não caber nos 128 mil tokens de saída de uma chamada (~2 h de fala); se um dia passar, é erro explícito.
MAX_PALAVRAS_POR_CHAMADA = 14_000
ENCOLHIMENTO_MAXIMO = 0.30

INSTRUCOES = """Você revisa transcrições automáticas de aulas de pós-graduação em dermatologia veterinária.
Tema desta aula: {aula}.

Você recebe a transcrição bruta de um áudio da aula, gravado por celular a certa distância do professor, com ruído. Cada parágrafo começa com o tempo [hh:mm:ss] e um rótulo de falante (Falante A, Falante B...) atribuído automaticamente; a diarização pode errar.

Produza a transcrição integral limpa desse áudio.

Fidelidade é a regra principal:
- Não resuma, não corte, não reordene e não acrescente nada que não foi dito. Todo conteúdo permanece: explicações, exemplos, casos clínicos, números, doses, nomes de fármacos, comentários, avisos e digressões.
- Remova apenas vícios de fala: hesitações (é, ééé, hã, hum), muletas sem função ("né", "tá", "tipo", "então" repetidos), falsos começos e repetições imediatas da mesma palavra ou frase.
- Corrija pontuação, ortografia e concordância em português do Brasil, sem reescrever o estilo do professor.
- Corrija termos técnicos mal reconhecidos usando o contexto e o glossário abaixo (por exemplo, "estrato corneo" para "estrato córneo"). Se a correção não for evidente, mantenha o que foi transcrito e acrescente [?] logo depois do termo.
- Trecho ininteligível, cortado ou sem sentido recuperável: escreva [inaudível]. Nunca preencha lacunas com suposições.

Falantes:
- Identifique o professor (normalmente o falante dominante) e marque suas falas com **Professor:**.
- Falas de alunos: **Aluno(a) — pergunta:** quando for pergunta; **Aluno(a):** nos demais casos. Se houver outro docente, **Professor(a) 2:**.
- Se a diarização trocou o falante no meio de uma frase óbvia do professor, corrija.

Formato:
- Parágrafos por unidade de ideia. Cada parágrafo começa com o tempo [hh:mm:ss] do parágrafo bruto de onde ele vem, seguido do rótulo do falante.
- Responda somente com a transcrição limpa em Markdown, sem título, comentários ou preâmbulo.

Glossário de referência (termos que podem aparecer):
{glossario}"""

_MARCACOES = re.compile(r"\[\d{1,2}:\d{2}:\d{2}\]|\*\*[^*]+:\*\*|\[inaudível\]|\[\?\]")


def contar_palavras(texto: str) -> int:
    return len(_MARCACOES.sub(" ", texto).split())


def limpar(claude: Claude, audio: Audio, bruta: Path, aula: str, glossario: list[str]) -> Path:
    destino = bruta.with_name(f"{audio.nome_base}.limpa.md")
    if destino.exists():
        log.info("Áudio %d: transcrição limpa em cache", audio.posicao)
        return destino
    texto_bruto = bruta.read_text(encoding="utf-8")
    palavras_brutas = contar_palavras(texto_bruto)
    if palavras_brutas > MAX_PALAVRAS_POR_CHAMADA:
        raise RuntimeError(f"Áudio {audio.posicao} tem {palavras_brutas} palavras, acima do limite seguro de "
                           f"{MAX_PALAVRAS_POR_CHAMADA} para uma chamada. Divida o áudio antes de processar.")
    log.info("Áudio %d: limpando transcrição (%d palavras)", audio.posicao, palavras_brutas)
    system = [{"type": "text", "cache_control": {"type": "ephemeral"},
               "text": INSTRUCOES.format(aula=aula, glossario="\n".join(glossario))}]
    resposta = claude.gerar("limpeza", audio.nome_base, system, texto_bruto)
    palavras_limpas = contar_palavras(resposta.texto)
    proporcao = palavras_limpas / palavras_brutas
    log.info("Áudio %d: %d palavras brutas -> %d limpas (%.0f%%)", audio.posicao, palavras_brutas,
             palavras_limpas, proporcao * 100)
    if proporcao < 1 - ENCOLHIMENTO_MAXIMO:
        rejeitada = destino.with_suffix(".rejeitada.md")
        rejeitada.write_text(resposta.texto, encoding="utf-8")
        raise RuntimeError(f"Áudio {audio.posicao}: a transcrição limpa encolheu {1 - proporcao:.0%} em relação "
                           f"à bruta (limite {ENCOLHIMENTO_MAXIMO:.0%}). Resultado guardado em {rejeitada.name} "
                           "para inspeção; a rodada parou.")
    destino.write_text(resposta.texto.strip() + "\n", encoding="utf-8")
    return destino
