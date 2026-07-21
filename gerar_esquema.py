#!/usr/bin/env python3
"""
Gera esquematico da fonte de LEDs (Schemdraw) a partir de leds.json
e do calculo de resistores (calcular_resistores.py).

Uso:
  python gerar_esquema.py
  python gerar_esquema.py --fator 0.5 --out esquema_fonte.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import schemdraw.elements as elm
from schemdraw import Drawing

from calcular_resistores import calc_for_led, format_ohms, load_config


def build_results(cfg: dict, current_factor: float, power_derate: float) -> dict[str, dict]:
    leds_by_id = {led["id"]: led for led in cfg["leds"]}
    out: dict[str, dict] = {}
    for supply in cfg["supplies_V"].values():
        vs = float(supply["voltage"])
        for led_id in supply["leds"]:
            out[led_id] = calc_for_led(leds_by_id[led_id], vs, current_factor, power_derate)
    return out


def branch_info(led: dict, res: dict) -> tuple[str, str, bool]:
    wl = led.get("wavelength_nm", "")
    led_lbl = f"{led['id']}\n{wl} nm"
    if not res.get("ok") or not res.get("suggestions"):
        return f"CC ~{res['I_target_mA']:.0f} mA", led_lbl + "\n(driver)", True
    sug = res["suggestions"][0]
    r_lbl = f"{format_ohms(sug['R_ohm'])}\n{sug['P_rated_suggested_W']:g} W"
    led_lbl = f"{led_lbl}\n~{sug['I_mA_Vf_typ']:.0f} mA"
    return r_lbl, led_lbl, False


def draw_parallel_supply(
    d: Drawing,
    *,
    origin: tuple[float, float],
    vs: float,
    title: str,
    branches: list[tuple[dict, dict]],
    spacing: float = 3.2,
) -> None:
    """Desenha fonte Vs com N ramos em paralelo (R+LED ou SourceI+LED)."""
    x0, y_gnd = origin
    n = len(branches)
    rail_w = max((n - 1) * spacing + 1.0, 1.5)

    d.add(elm.Label().at((x0, y_gnd + 7.2)).label(title, fontsize=11, halign="left"))

    # Fonte
    d.add(elm.Ground().at((x0, y_gnd)))
    src = d.add(elm.SourceV().up().at((x0, y_gnd)).label(f"{vs:g} V", loc="left"))
    y_rail = src.end[1]
    d.add(elm.Dot().at((x0, y_rail)))

    # Trilhos
    d.add(elm.Line().right().at((x0, y_rail)).length(rail_w))
    d.add(elm.Line().right().at((x0, y_gnd)).length(rail_w))

    for i, (led, res) in enumerate(branches):
        x = x0 + 0.6 + i * spacing
        r_lbl, led_lbl, use_cc = branch_info(led, res)

        d.add(elm.Dot().at((x, y_rail)))
        if use_cc:
            elem = d.add(
                elm.SourceI().down().at((x, y_rail)).label(r_lbl, loc="right", fontsize=9)
            )
        else:
            elem = d.add(
                elm.Resistor().down().at((x, y_rail)).label(r_lbl, loc="right", fontsize=9)
            )
        d.add(elm.LED().down().at(elem.end).label(led_lbl, loc="right", fontsize=9))
        # Fecha ate o GND (LED ja desce ~1 unit; completa o fio)
        d.add(elm.Line().down().to((x, y_gnd)))
        d.add(elm.Dot().at((x, y_gnd)))


def generate_drawing(cfg: dict, results: dict[str, dict], current_factor: float) -> Drawing:
    leds_by_id = {led["id"]: led for led in cfg["leds"]}
    d = Drawing(unit=2.5, fontsize=10)

    d.add(
        elm.Label()
        .at((0, 9.0))
        .label(
            f"Fonte optica LEDs UV - Litel / UFJF\n"
            f"Resistores calculados a {current_factor:.0%} de I_max (serie E24, arredondado para cima)",
            fontsize=12,
            halign="left",
        )
    )

    s5 = cfg["supplies_V"]["5V"]
    branches5 = [(leds_by_id[i], results[i]) for i in s5["leds"]]
    draw_parallel_supply(
        d,
        origin=(0.0, 0.0),
        vs=float(s5["voltage"]),
        title="Barramento 5 V",
        branches=branches5,
        spacing=3.4,
    )

    # 12 V a direita do bloco 5 V
    s12 = cfg["supplies_V"]["12V"]
    branches12 = [(leds_by_id[i], results[i]) for i in s12["leds"]]
    n5 = len(branches5)
    x12 = 0.6 + (n5 - 1) * 3.4 + 4.0
    draw_parallel_supply(
        d,
        origin=(x12, 0.0),
        vs=float(s12["voltage"]),
        title="Barramento 12 V",
        branches=branches12,
        spacing=3.4,
    )

    d.add(
        elm.Label()
        .at((0.0, -1.3))
        .label(
            "Nota: LED-04 (Vf ~ 5 V com fonte 5 V) desenhado com driver de corrente constante.",
            fontsize=9,
            halign="left",
            color="dimgray",
        )
    )
    return d


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera esquematico Schemdraw da fonte de LEDs.")
    parser.add_argument("--json", type=Path, default=Path(__file__).with_name("leds.json"))
    parser.add_argument("--fator", type=float, default=0.7)
    parser.add_argument("--derate", type=float, default=0.5)
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("esquema_fonte.png"))
    args = parser.parse_args()

    if not args.json.is_file():
        print(f"Erro: arquivo nao encontrado: {args.json}", file=sys.stderr)
        return 1

    cfg = load_config(args.json)
    results = build_results(cfg, args.fator, args.derate)
    drawing = generate_drawing(cfg, results, args.fator)

    drawing.save(str(args.out), dpi=200)
    print(f"Esquematico salvo em: {args.out.resolve()}")
    print(f"BBox: {drawing.get_bbox()}")

    if args.out.suffix.lower() == ".png":
        svg = args.out.with_suffix(".svg")
        drawing.save(str(svg))
        print(f"SVG salvo em: {svg.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
