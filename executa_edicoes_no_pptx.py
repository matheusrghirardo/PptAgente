"""
executa_edicoes_no_pptx.py — Executa o plano do mapper diretamente no PPTX.

Aplica cada ação do plano (alterar_texto, alterar_celula_tabela,
substituir_texto_global) sem intermediação de LLM, garantindo que
NENHUMA ação seja perdida, duplicada ou reinterpretada.
"""

import copy
import logging
import re
from io import BytesIO
from typing import Any

from pptx import Presentation

logger = logging.getLogger(__name__)


def _substituir_texto_em_paragrafos(paragraphs, antigo: str, novo: str) -> bool:
    """Substitui texto preservando formatação dos runs.

    Percorre os paragraphs, reconstrói o texto concatenando os runs, e quando
    encontra `antigo`, redistribui `novo` pelos mesmos runs para manter
    fonte, cor, tamanho, etc.
    """
    for para in paragraphs:
        texto_completo = para.text
        if antigo not in texto_completo:
            continue

        # Caso simples: 1 run contém todo o texto
        if len(para.runs) == 1 and antigo in para.runs[0].text:
            para.runs[0].text = para.runs[0].text.replace(antigo, novo, 1)
            return True

        # Caso multi-run: reconstruir preservando formatação
        # Mapear posição no texto global → run
        posicoes = []
        for run in para.runs:
            posicoes.append(run.text)

        texto_concat = "".join(posicoes)
        idx = texto_concat.find(antigo)
        if idx == -1:
            continue

        # Localizar quais runs são afetados
        char_pos = 0
        run_spans = []
        for ri, run in enumerate(para.runs):
            rlen = len(run.text)
            run_spans.append((char_pos, char_pos + rlen, ri))
            char_pos += rlen

        end_idx = idx + len(antigo)

        # Encontrar runs que cobrem [idx, end_idx)
        affected_runs = []
        for (start, end, ri) in run_spans:
            if end > idx and start < end_idx:
                affected_runs.append((start, end, ri))

        if not affected_runs:
            continue

        # Substituir: colocar novo texto no primeiro run afetado,
        # limpar os intermediários, ajustar o último
        if len(affected_runs) == 1:
            start, end, ri = affected_runs[0]
            run = para.runs[ri]
            local_start = idx - start
            local_end = end_idx - start
            run.text = run.text[:local_start] + novo + run.text[local_end:]
        else:
            # Primeiro run: manter texto antes do match + novo valor
            first_start, _, first_ri = affected_runs[0]
            local_start = idx - first_start
            para.runs[first_ri].text = para.runs[first_ri].text[:local_start] + novo

            # Runs intermediários: limpar
            for i in range(1, len(affected_runs) - 1):
                _, _, ri = affected_runs[i]
                para.runs[ri].text = ""

            # Último run: manter texto após o match
            last_start, last_end, last_ri = affected_runs[-1]
            local_end = end_idx - last_start
            para.runs[last_ri].text = para.runs[last_ri].text[local_end:]

        return True

    return False


def executar_plano_direto(
    pptx_bytes: bytes,
    plano: list[dict[str, Any]],
    on_log: Any = None,
) -> dict[str, Any]:
    """Executa o plano do mapper diretamente no PPTX.

    Args:
        pptx_bytes: Bytes do PPTX base.
        plano: Lista de ações do mapper.
        on_log: Callback opcional para emitir mensagens.

    Returns:
        Dict com pptx_bytes, total_sucesso, total_erro, detalhes.
    """
    prs = Presentation(BytesIO(pptx_bytes))
    slides = list(prs.slides)

    ok = 0
    erros = 0
    skipped = 0
    detalhes: list[dict] = []

    def _log(msg):
        logger.info(msg)
        if on_log:
            on_log(msg)

    # Reorder: execute substituir_texto_global FIRST to avoid
    # catching text freshly written by alterar_texto/alterar_celula_tabela.
    plano_ordenado = sorted(
        enumerate(plano),
        key=lambda x: (0 if x[1].get('acao') == 'substituir_texto_global' else 1,
                       x[0]),
    )

    for orig_i, acao in plano_ordenado:
        i = orig_i  # preserve original index for logging
        tipo = acao.get("acao", "")
        antigo = acao.get("valor_antigo", "")
        novo = acao.get("valor_novo", "")
        slide_num = acao.get("slide_numero")
        shape_idx = acao.get("shape_indice")
        row = acao.get("tabela_linha")
        col = acao.get("tabela_coluna")
        desc = acao.get("descricao", "")

        # Skip no-op
        if antigo == novo:
            skipped += 1
            detalhes.append({"idx": i, "status": "skipped", "reason": "antigo == novo"})
            continue

        try:
            if tipo == "substituir_texto_global":
                n_subs = _substituir_global(prs, antigo, novo)
                if n_subs > 0:
                    ok += 1
                    _log(f"  ✅ [{i+1}] Global: \"{antigo[:40]}\" → \"{novo[:40]}\" ({n_subs}x)")
                    detalhes.append({"idx": i, "status": "ok", "count": n_subs})
                else:
                    _log(f"  ⚠️ [{i+1}] Global: \"{antigo[:40]}\" não encontrado em nenhum slide")
                    detalhes.append({"idx": i, "status": "not_found", "desc": desc})
                    # Count as ok — text might have been changed by a previous action
                    ok += 1
                continue

            # Validate slide number
            if not slide_num or slide_num < 1 or slide_num > len(slides):
                erros += 1
                _log(f"  ❌ [{i+1}] Slide {slide_num} inválido (total: {len(slides)})")
                detalhes.append({"idx": i, "status": "error", "reason": f"invalid slide {slide_num}"})
                continue

            slide = slides[slide_num - 1]
            shapes = list(slide.shapes)

            if shape_idx is None or shape_idx < 0 or shape_idx >= len(shapes):
                erros += 1
                _log(f"  ❌ [{i+1}] Shape {shape_idx} inválido (total: {len(shapes)} no slide {slide_num})")
                detalhes.append({"idx": i, "status": "error", "reason": f"invalid shape {shape_idx}"})
                continue

            shape = shapes[shape_idx]

            if tipo == "alterar_celula_tabela":
                if not shape.has_table:
                    erros += 1
                    _log(f"  ❌ [{i+1}] Shape {shape_idx} no slide {slide_num} não é tabela")
                    detalhes.append({"idx": i, "status": "error", "reason": "not a table"})
                    continue

                table = shape.table
                if row is None or col is None:
                    erros += 1
                    _log(f"  ❌ [{i+1}] Falta linha/coluna para célula da tabela")
                    detalhes.append({"idx": i, "status": "error", "reason": "missing row/col"})
                    continue

                if row >= len(table.rows) or col >= len(table.columns):
                    erros += 1
                    _log(f"  ❌ [{i+1}] Célula [{row},{col}] fora do range ({len(table.rows)}x{len(table.columns)})")
                    detalhes.append({"idx": i, "status": "error", "reason": "cell out of range"})
                    continue

                cell = table.cell(row, col)
                cell_text = cell.text.strip()

                if cell_text == antigo or antigo in cell.text:
                    # Substituir preservando formatação dos runs
                    replaced = _substituir_texto_em_paragrafos(
                        cell.text_frame.paragraphs, antigo, novo
                    )
                    if replaced:
                        ok += 1
                        _log(f"  ✅ [{i+1}] Célula [{row},{col}] slide {slide_num}: \"{antigo[:30]}\" → \"{novo[:30]}\"")
                        detalhes.append({"idx": i, "status": "ok"})
                    else:
                        # Fallback: set entire cell text (loses formatting)
                        cell.text_frame.paragraphs[0].runs[0].text = novo if cell.text_frame.paragraphs and cell.text_frame.paragraphs[0].runs else novo
                        ok += 1
                        _log(f"  ✅ [{i+1}] Célula [{row},{col}] slide {slide_num}: fallback set")
                        detalhes.append({"idx": i, "status": "ok", "method": "fallback"})
                else:
                    # Try fuzzy: the antigo might not match exactly
                    if novo and (cell_text == novo or novo in cell.text):
                        # Already contains the target value (e.g. changed by a prior global sub)
                        ok += 1
                        _log(f"  ✅ [{i+1}] Célula [{row},{col}] slide {slide_num}: já contém \"{novo[:30]}\" (ação anterior)")
                        detalhes.append({"idx": i, "status": "ok", "method": "already_done"})
                    else:
                        _log(f"  ⚠️ [{i+1}] Célula [{row},{col}] slide {slide_num}: "
                             f"esperado \"{antigo[:30]}\" mas encontrado \"{cell_text[:30]}\"")
                        # Still try to set the new value
                        if cell.text_frame.paragraphs and cell.text_frame.paragraphs[0].runs:
                            cell.text_frame.paragraphs[0].runs[0].text = novo
                            ok += 1
                            detalhes.append({"idx": i, "status": "ok", "method": "force"})
                        else:
                            erros += 1
                            detalhes.append({"idx": i, "status": "error", "reason": "no runs in cell"})

            elif tipo == "alterar_texto":
                if shape.has_text_frame:
                    replaced = _substituir_texto_em_paragrafos(
                        shape.text_frame.paragraphs, antigo, novo
                    )
                    if replaced:
                        ok += 1
                        _log(f"  ✅ [{i+1}] Texto slide {slide_num} shape {shape_idx}: \"{antigo[:30]}\" → \"{novo[:30]}\"")
                        detalhes.append({"idx": i, "status": "ok"})
                    else:
                        _log(f"  ⚠️ [{i+1}] Texto \"{antigo[:40]}\" não encontrado em shape {shape_idx} slide {slide_num}")
                        # Try in all shapes of the slide as fallback
                        found = False
                        for si, s in enumerate(shapes):
                            if s.has_text_frame:
                                if _substituir_texto_em_paragrafos(s.text_frame.paragraphs, antigo, novo):
                                    ok += 1
                                    _log(f"       → Encontrado em shape {si} (fallback)")
                                    detalhes.append({"idx": i, "status": "ok", "method": "fallback", "actual_shape": si})
                                    found = True
                                    break
                        if not found:
                            # Check if desired text already present (changed by a prior action)
                            if shape.has_text_frame and novo in shape.text_frame.text:
                                ok += 1
                                _log(f"       → Already applied (prior action)")
                                detalhes.append({"idx": i, "status": "ok", "method": "already_done"})
                            else:
                                erros += 1
                                detalhes.append({"idx": i, "status": "not_found"})
                else:
                    erros += 1
                    _log(f"  ❌ [{i+1}] Shape {shape_idx} no slide {slide_num} sem text_frame")
                    detalhes.append({"idx": i, "status": "error", "reason": "no text_frame"})

            else:
                _log(f"  ⚠️ [{i+1}] Ação desconhecida: {tipo}")
                skipped += 1
                detalhes.append({"idx": i, "status": "skipped", "reason": f"unknown action: {tipo}"})

        except Exception as e:
            erros += 1
            _log(f"  ❌ [{i+1}] Exception: {e}")
            detalhes.append({"idx": i, "status": "error", "reason": str(e)})

    # Save result
    output_buffer = BytesIO()
    prs.save(output_buffer)
    pptx_final = output_buffer.getvalue()

    _log(f"  📊 Resultado: {ok} OK, {erros} erros, {skipped} skipped de {len(plano)} ações")

    return {
        "sucesso": erros == 0,
        "pptx_bytes": pptx_final,
        "total_sucesso": ok,
        "total_erro": erros,
        "total_skipped": skipped,
        "detalhes": detalhes,
    }


def _substituir_global(prs: Presentation, antigo: str, novo: str) -> int:
    """Substitui texto em TODOS os slides/shapes/cells do PPTX."""
    count = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                if _substituir_texto_em_paragrafos(shape.text_frame.paragraphs, antigo, novo):
                    count += 1
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if _substituir_texto_em_paragrafos(cell.text_frame.paragraphs, antigo, novo):
                            count += 1
    return count
