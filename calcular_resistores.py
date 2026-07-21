#!/usr/bin/env python3
"""
Calcula resistores série para os LEDs da fonte óptica (Litel / UFJF).

  R = (Vs - Vf) / I
  P_R = I^2 * R

Estratégia conservadora (proteger o LED):
  - corrente alvo = I_max * fator (< 1)
  - R mínimo = (Vs - Vf_min) / I_alvo  → arredonda PARA CIMA na série E24
  - potência do resistor com folga (derating)

Uso:
  python calcular_resistores.py
  python calcular_resistores.py --fator 0.5
  python calcular_resistores.py --json leds.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Série E24 (5 %), valores base 1.0 … 9.1
E24_BASE = [
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7,
    3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1,
]

# Potências comerciais comuns (W)
RESISTOR_POWERS_W = [0.125, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]


def e24_series(r_min: float = 0.1, r_max: float = 1e6) -> list[float]:
    """Gera valores E24 entre r_min e r_max."""
    values: list[float] = []
    decade = 0.1
    while decade <= r_max * 10:
        for b in E24_BASE:
            r = b * decade
            if r_min - 1e-12 <= r <= r_max + 1e-12:
                values.append(round(r, 10))
        decade *= 10
    return values


def next_e24_up(r_ideal: float, series: list[float] | None = None) -> float | None:
    """Menor valor da série ≥ r_ideal (mais corrente baixa → mais seguro para o LED)."""
    if r_ideal <= 0:
        return None
    series = series or e24_series()
    for r in series:
        if r + 1e-12 >= r_ideal:
            return r
    return series[-1] if series else None


def nearest_e24(r_ideal: float, series: list[float] | None = None) -> float | None:
    series = series or e24_series()
    if not series or r_ideal <= 0:
        return None
    return min(series, key=lambda r: abs(r - r_ideal))


def format_ohms(r: float) -> str:
    if r >= 1e6:
        return f"{r / 1e6:.3g} Mohm"
    if r >= 1e3:
        return f"{r / 1e3:.3g} kohm"
    if r >= 10:
        return f"{r:.3g} ohm"
    return f"{r:.2f} ohm"


def pick_resistor_power(p_diss_w: float, derate: float = 0.5) -> float:
    """
    Escolhe potência comercial tal que P_rated * derate >= P_diss.
    derate=0.5 → resistor trabalha no máximo a 50% da potência nominal.
    """
    need = p_diss_w / derate if derate > 0 else p_diss_w
    for p in RESISTOR_POWERS_W:
        if p + 1e-12 >= need:
            return p
    return RESISTOR_POWERS_W[-1]


def calc_for_led(
    led: dict,
    vs: float,
    current_factor: float,
    power_derate: float,
) -> dict:
    led_id = led["id"]
    vf = float(led["Vf_V"])
    vf_min = float(led.get("Vf_min_V", vf))
    vf_max = float(led.get("Vf_max_V", vf))
    i_max_a = float(led["I_max_mA"]) / 1000.0
    i_target_a = i_max_a * current_factor

    headroom_typ = vs - vf
    headroom_min = vs - vf_min  # maior queda no resistor → maior corrente possível
    headroom_max = vs - vf_max

    result = {
        "id": led_id,
        "name": led.get("name", ""),
        "Vs_V": vs,
        "Vf_V": vf,
        "Vf_min_V": vf_min,
        "Vf_max_V": vf_max,
        "I_max_mA": led["I_max_mA"],
        "I_target_mA": round(i_target_a * 1000, 1),
        "ok": True,
        "warnings": [],
        "suggestions": [],
    }

    if led.get("note"):
        result["warnings"].append(led["note"])

    if headroom_min <= 0:
        result["ok"] = False
        result["warnings"].append(
            f"Headroom insuficiente: Vs={vs} V <= Vf_min={vf_min} V. "
            "Resistor serie nao limita corrente de forma util; use driver de corrente constante "
            "ou aumente a tensao da fonte."
        )
        return result

    # R mínimo para I ≤ I_alvo no pior caso (Vf = Vf_min)
    r_ideal = headroom_min / i_target_a
    r_e24 = next_e24_up(r_ideal)
    r_near = nearest_e24(r_ideal)

    if r_e24 is None:
        result["ok"] = False
        result["warnings"].append("Nao foi possivel escolher valor E24.")
        return result

    def row(r: float, label: str) -> dict:
        # correntes nos extremos de Vf
        i_at_vf_min = headroom_min / r
        i_at_vf = (vs - vf) / r if (vs - vf) > 0 else 0.0
        i_at_vf_max = headroom_max / r if headroom_max > 0 else 0.0
        # potência máxima no resistor (pior caso: Vf mínimo → maior I)
        p_r = (i_at_vf_min ** 2) * r
        p_rated = pick_resistor_power(p_r, derate=power_derate)
        return {
            "label": label,
            "R_ohm": r,
            "R_display": format_ohms(r),
            "I_mA_Vf_min": round(i_at_vf_min * 1000, 1),
            "I_mA_Vf_typ": round(i_at_vf * 1000, 1),
            "I_mA_Vf_max": round(max(i_at_vf_max, 0) * 1000, 1),
            "P_resistor_W": round(p_r, 3),
            "P_rated_suggested_W": p_rated,
            "safe_for_led": i_at_vf_min <= i_max_a * 1.001,
        }

    result["R_ideal_ohm"] = round(r_ideal, 3)
    result["suggestions"] = [
        row(r_e24, "recomendado (E24 >= ideal, corrente menor)"),
    ]
    if r_near is not None and abs(r_near - r_e24) > 1e-9:
        result["suggestions"].append(row(r_near, "E24 mais proximo do ideal"))

    # Uma opção ainda mais conservadora: próximo E24 acima do recomendado
    series = e24_series()
    idx = series.index(r_e24) if r_e24 in series else -1
    if 0 <= idx < len(series) - 1:
        r_safer = series[idx + 1]
        result["suggestions"].append(row(r_safer, "mais conservador (proximo E24 acima)"))

    rec = result["suggestions"][0]
    if not rec["safe_for_led"]:
        result["warnings"].append(
            "A corrente no pior caso (Vf minimo) ainda pode exceder I_max; aumente R."
        )
    if rec["P_resistor_W"] > 1.0:
        result["warnings"].append(
            f"Dissipacao alta no resistor (~{rec['P_resistor_W']} W). "
            "Prefira resistor de potencia ou driver CC."
        )

    return result


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def print_report(results: list[dict], current_factor: float, power_derate: float) -> None:
    print("=" * 72)
    print("Sugestao de resistores serie - Fonte LEDs UV (Litel / UFJF)")
    print(f"Fator de corrente: {current_factor:.0%} de I_max  |  "
          f"Derating potencia resistor: {power_derate:.0%}")
    print("=" * 72)

    for res in results:
        print()
        print(f"### {res['id']} - {res['name']}")
        print(f"    Fonte Vs = {res['Vs_V']} V  |  "
              f"Vf = {res['Vf_V']} V (min {res['Vf_min_V']} ... max {res['Vf_max_V']})")
        print(f"    I_max = {res['I_max_mA']} mA  ->  I_alvo = {res['I_target_mA']} mA")

        for w in res["warnings"]:
            print(f"    ! {w}")

        if not res["ok"]:
            continue

        print(f"    R ideal = {res['R_ideal_ohm']} ohm")
        print(f"    {'Opcao':<42} {'R':>8} {'I@Vfmin':>9} {'I@typ':>8} {'P_R':>7} {'Pnom':>6}")
        print(f"    {'-'*42} {'-'*8} {'-'*9} {'-'*8} {'-'*7} {'-'*6}")
        for s in res["suggestions"]:
            flag = "ok" if s["safe_for_led"] else "!!"
            print(
                f"    {s['label']:<42} {s['R_display']:>8} "
                f"{s['I_mA_Vf_min']:>7.1f} mA {s['I_mA_Vf_typ']:>6.1f} mA "
                f"{s['P_resistor_W']:>5.2f} W {s['P_rated_suggested_W']:>4g} W {flag}"
            )

    print()
    print("Notas:")
    print("  - R arredondado para CIMA na E24 reduz a corrente (protege o LED).")
    print("  - Pnom: potencia comercial sugerida com derating (nao operar no limite).")
    print("  - Valide Vf e corrente reais em bancada antes do uso continuo.")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calcula resistores série para LEDs.")
    parser.add_argument(
        "--json",
        type=Path,
        default=Path(__file__).with_name("leds.json"),
        help="Arquivo JSON com specs (default: leds.json)",
    )
    parser.add_argument(
        "--fator",
        type=float,
        default=0.7,
        help="Fração de I_max usada como corrente alvo (default: 0.7)",
    )
    parser.add_argument(
        "--derate",
        type=float,
        default=0.5,
        help="Fração da potência nominal do resistor a usar (default: 0.5)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Opcional: salvar resultado em JSON",
    )
    args = parser.parse_args()

    if not (0 < args.fator <= 1):
        print("Erro: --fator deve estar em (0, 1].", file=sys.stderr)
        return 1
    if not (0 < args.derate <= 1):
        print("Erro: --derate deve estar em (0, 1].", file=sys.stderr)
        return 1
    if not args.json.is_file():
        print(f"Erro: arquivo não encontrado: {args.json}", file=sys.stderr)
        return 1

    cfg = load_config(args.json)
    leds_by_id = {led["id"]: led for led in cfg["leds"]}
    results: list[dict] = []

    for supply_name, supply in cfg["supplies_V"].items():
        vs = float(supply["voltage"])
        for led_id in supply["leds"]:
            led = leds_by_id.get(led_id)
            if not led:
                print(f"Aviso: LED {led_id} não está em leds.json", file=sys.stderr)
                continue
            results.append(
                calc_for_led(led, vs=vs, current_factor=args.fator, power_derate=args.derate)
            )

    print_report(results, args.fator, args.derate)

    if args.out:
        payload = {
            "current_factor": args.fator,
            "power_derate": args.derate,
            "results": results,
        }
        args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nResultado salvo em: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
