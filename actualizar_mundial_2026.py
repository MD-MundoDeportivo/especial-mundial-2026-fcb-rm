#!/usr/bin/env python3
import argparse
import csv
import json
import ssl
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


RAW_BASE = "https://raw.githubusercontent.com/Bustami/efi-fifa-data-wc-2026/refs/heads/master/data"
EFI_URL = f"{RAW_BASE}/wc2026_efi.csv"
MATCHES_URL = f"{RAW_BASE}/wc2026_matches.csv"
RESULT_KEYS = {
    "w": "win",
    "win": "win",
    "victoria": "win",
    "v": "win",
    "d": "draw",
    "draw": "draw",
    "empate": "draw",
    "e": "draw",
    "l": "loss",
    "loss": "loss",
    "derrota": "loss",
}


def normalized(value):
    value = value or ""
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.split())


def fetch_text(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8-sig")
    except (urllib.error.URLError, ssl.SSLError):
        try:
            completed = subprocess.run(
                ["curl", "-fsSL", url],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(f"No se pudo descargar {url}") from exc
        return completed.stdout


def read_csv_url(url):
    return list(csv.DictReader(fetch_text(url).splitlines()))


def read_results(path):
    path = Path(path)
    if not path.exists():
        return {}

    rows = csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines())
    results = {}
    for row in rows:
        result_id = (row.get("result_id") or "").strip()
        team = (row.get("team") or "").strip().upper()
        result = normalized(row.get("result"))
        if not result_id or not team or not result:
            continue
        if result not in RESULT_KEYS:
            raise ValueError(f"Resultado no valido en {path}: {result_id} {team} {row.get('result')}")
        results[(result_id, team)] = RESULT_KEYS[result]
    return results


def compute_results(efi_rows, match_rows):
    """Deduce victoria/empate/derrota de cada seleccion a partir de los goles del
    dataset EFI. El marcador de un equipo es la suma de goles de sus jugadores mas
    los goles en propia del rival. No usa marcadores externos: el repositorio fuente
    no los publica, pero la suma de goles reproduce el resultado de cada partido."""
    goals_by_team = {}
    owngoals_by_team = {}
    code_by_team_id = {}

    for row in efi_rows:
        key = (row.get("match_id"), row.get("team_id"))
        goals_by_team[key] = goals_by_team.get(key, 0) + to_int(row.get("goals"))
        owngoals_by_team[key] = owngoals_by_team.get(key, 0) + to_int(row.get("own_goals"))
        if row.get("team_id") and row.get("team_name"):
            code_by_team_id[row["team_id"]] = row["team_name"]

    results = {}
    for match in match_rows:
        match_id = match.get("result_id")
        home_id = match.get("home_team_id")
        away_id = match.get("away_team_id")
        home_key = (match_id, home_id)
        away_key = (match_id, away_id)
        # Si ninguno de los dos equipos aparece en EFI, el partido aun no se ha jugado.
        if home_key not in goals_by_team and away_key not in goals_by_team:
            continue

        home_score = goals_by_team.get(home_key, 0) + owngoals_by_team.get(away_key, 0)
        away_score = goals_by_team.get(away_key, 0) + owngoals_by_team.get(home_key, 0)

        if home_score > away_score:
            home_result, away_result = "win", "loss"
        elif home_score < away_score:
            home_result, away_result = "loss", "win"
        else:
            home_result = away_result = "draw"

        home_code = code_by_team_id.get(home_id)
        away_code = code_by_team_id.get(away_id)
        if home_code:
            results[(match_id, home_code)] = home_result
        if away_code:
            results[(match_id, away_code)] = away_result

    return results


def to_int(value):
    if value in (None, "", "NA", "N/A"):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def to_float(value):
    if value in (None, "", "NA", "N/A"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_date(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def match_context(row, matches_by_result_id, results_by_match_team):
    match = matches_by_result_id.get(row["match_id"], {})
    team_id = row.get("team_id")
    side = None
    opponent = None

    if match:
        if team_id == match.get("home_team_id"):
            side = "home"
            opponent = match.get("away_team")
        elif team_id == match.get("away_team_id"):
            side = "away"
            opponent = match.get("home_team")

    matches_played = to_int(row.get("matches_played"))
    result = results_by_match_team.get((row.get("match_id"), row.get("team_name")))

    return {
        "result_id": row.get("match_id"),
        "fifa_match_id": match.get("match_id"),
        "date": match.get("date"),
        "stage": match.get("stage"),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "side": side,
        "opponent": opponent,
        "team": row.get("team_name"),
        "result": result,
        "matches_played": matches_played,
        "goals": to_int(row.get("goals")),
        "assists": to_int(row.get("assists")),
        "minutes": round(to_float(row.get("time_played")), 1),
        "wins": 1 if matches_played and result == "win" else 0,
        "draws": 1 if matches_played and result == "draw" else 0,
        "losses": 1 if matches_played and result == "loss" else 0,
        "result_pending": 1 if matches_played and not result else 0,
        "yellow_cards": to_int(row.get("yellow_cards")),
        "red_cards": to_int(row.get("red_cards")),
    }


def fixture_context(match, team_id):
    side = "home" if team_id == match.get("home_team_id") else "away"
    opponent = match.get("away_team") if side == "home" else match.get("home_team")

    return {
        "result_id": match.get("result_id"),
        "fifa_match_id": match.get("match_id"),
        "date": match.get("date"),
        "stage": match.get("stage"),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "side": side,
        "opponent": opponent,
    }


def build_payload(config, efi_rows, match_rows, results_by_match_team):
    rows_by_player = {}
    team_id_by_code = {}
    for row in efi_rows:
        rows_by_player.setdefault(normalized(row.get("player_name")), []).append(row)
        if row.get("team_name") and row.get("team_id"):
            team_id_by_code[row["team_name"]] = row["team_id"]

    matches_by_result_id = {row["result_id"]: row for row in match_rows}
    generated_at = datetime.now(timezone.utc)

    payload = {
        "source": {
            "repository": "https://github.com/Bustami/efi-fifa-data-wc-2026",
            "efi_url": EFI_URL,
            "matches_url": MATCHES_URL,
            "generated_at": generated_at.isoformat(),
            "notes": [
                "Club ownership comes from jugadores_clubes.json, not from the FIFA dataset.",
                "time_played is rounded to minutes for the top-level minutes field.",
                "wins/draws/losses come from resultados_selecciones.csv because wc2026_matches.csv does not include scores.",
                "fixtures_pending counts future scheduled national-team matches, not player appearances.",
            ],
        },
        "clubs": {},
    }

    for club_id, club in config.items():
        players = []
        unique_team_matches = {}
        club_totals = {
            "matches_played": 0,
            "goals": 0,
            "assists": 0,
            "minutes": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "result_pending": 0,
            "fixtures_pending": 0,
            "yellow_cards": 0,
            "red_cards": 0,
        }
        fixtures_by_team = {}
        individual_total_keys = {"goals", "assists", "minutes", "yellow_cards", "red_cards"}

        for player in club.get("players", []):
            aliases = [normalized(alias) for alias in player.get("aliases", [])]
            national_team = (player.get("national_team") or "").upper()
            source_rows = []
            for alias in aliases:
                source_rows.extend(rows_by_player.get(alias, []))
            if national_team:
                source_rows = [row for row in source_rows if row.get("team_name") == national_team]

            seen = set()
            unique_rows = []
            for row in source_rows:
                key = (row.get("player_id"), row.get("match_id"))
                if key not in seen:
                    seen.add(key)
                    unique_rows.append(row)

            unique_rows.sort(key=lambda row: row.get("match_id", ""))
            appearances = [match_context(row, matches_by_result_id, results_by_match_team) for row in unique_rows]
            team_id = team_id_by_code.get(national_team)
            fixtures = []
            if team_id:
                for match in match_rows:
                    match_date = parse_date(match.get("date"))
                    if not match_date or match_date <= generated_at:
                        continue
                    if team_id not in {match.get("home_team_id"), match.get("away_team_id")}:
                        continue
                    fixture = fixture_context(match, team_id)
                    fixtures.append(fixture)
                    fixtures_by_team.setdefault(national_team, {})[match["result_id"]] = fixture

            totals = {
                "matches_played": sum(item["matches_played"] for item in appearances),
                "goals": sum(item["goals"] for item in appearances),
                "assists": sum(item["assists"] for item in appearances),
                "minutes_raw": round(sum(item["minutes"] for item in appearances), 1),
                "minutes": round(sum(item["minutes"] for item in appearances)),
                "wins": sum(item["wins"] for item in appearances),
                "draws": sum(item["draws"] for item in appearances),
                "losses": sum(item["losses"] for item in appearances),
                "result_pending": sum(item["result_pending"] for item in appearances),
                "fixtures_pending": len(fixtures),
                "yellow_cards": sum(item["yellow_cards"] for item in appearances),
                "red_cards": sum(item["red_cards"] for item in appearances),
            }

            for key in club_totals:
                if key in individual_total_keys:
                    club_totals[key] += totals[key]

            for item in appearances:
                if not item["matches_played"]:
                    continue
                unique_team_matches[(item["result_id"], item["team"])] = {
                    "result": item["result"],
                    "wins": item["wins"],
                    "draws": item["draws"],
                    "losses": item["losses"],
                    "result_pending": item["result_pending"],
                }

            first_row = unique_rows[0] if unique_rows else {}
            players.append(
                {
                    "id": player.get("id"),
                    "display_name": player.get("display_name"),
                    "source_name": first_row.get("player_name"),
                    "player_id": first_row.get("player_id"),
                    "national_team": national_team or first_row.get("team_name"),
                    "found": bool(unique_rows),
                    **totals,
                    "matches": appearances,
                    "fixtures": fixtures,
                }
            )

        club_totals["matches_played"] = len(unique_team_matches)
        club_totals["wins"] = sum(item["wins"] for item in unique_team_matches.values())
        club_totals["draws"] = sum(item["draws"] for item in unique_team_matches.values())
        club_totals["losses"] = sum(item["losses"] for item in unique_team_matches.values())
        club_totals["result_pending"] = sum(item["result_pending"] for item in unique_team_matches.values())
        unique_fixtures = {}
        for team_fixtures in fixtures_by_team.values():
            for result_id, fixture in team_fixtures.items():
                unique_fixtures[result_id] = fixture
        club_totals["fixtures_pending"] = len(unique_fixtures)

        payload["clubs"][club_id] = {
            "label": club.get("label", club_id),
            "totals": club_totals,
            "players": players,
            "fixtures": list(unique_fixtures.values()),
        }

    return payload


def collect_missing_results(payload):
    missing = {}
    for club in payload["clubs"].values():
        for player in club["players"]:
            for match in player["matches"]:
                if not match["matches_played"] or match["result"]:
                    continue
                key = (match["result_id"], match["team"])
                missing[key] = {
                    "result_id": match["result_id"],
                    "team": match["team"],
                    "date": match["date"],
                    "stage": match["stage"],
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                }
    return list(missing.values())


def write_outputs(payload, output_path, js_path, compact):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)

    if compact:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        data = json.dumps(payload, ensure_ascii=False, indent=2)

    output_path.write_text(data, encoding="utf-8")
    js_path.write_text(f"var MUNDIAL_2026_CLUBES = {data};\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Genera datos de jugadores FCB/RM para el Mundial 2026.")
    parser.add_argument("--players", default="jugadores_clubes.json", help="JSON con jugadores y aliases por club.")
    parser.add_argument("--results", default="resultados_selecciones.csv", help="CSV opcional con resultado por result_id y seleccion.")
    parser.add_argument("--out", default="data/mundial_2026_clubes.json", help="Ruta del JSON generado.")
    parser.add_argument("--js-out", default="data/mundial_2026_clubes.js", help="Ruta del JS con variable global generado.")
    parser.add_argument("--compact", action="store_true", help="Escribe JSON compacto.")
    args = parser.parse_args()

    config_path = Path(args.players)
    output_path = Path(args.out)
    js_path = Path(args.js_out)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    efi_rows = read_csv_url(EFI_URL)
    match_rows = read_csv_url(MATCHES_URL)
    # El resultado se calcula automaticamente desde los goles del dataset.
    # resultados_selecciones.csv queda solo como override manual opcional.
    computed_results = compute_results(efi_rows, match_rows)
    manual_results = read_results(args.results)
    results_by_match_team = {**computed_results, **manual_results}
    payload = build_payload(config, efi_rows, match_rows, results_by_match_team)
    payload["source"]["missing_results"] = collect_missing_results(payload)

    write_outputs(payload, output_path, js_path, args.compact)

    missing = [
        player["display_name"]
        for club in payload["clubs"].values()
        for player in club["players"]
        if not player["found"]
    ]
    print(f"OK: {output_path} actualizado")
    print(f"OK: {js_path} actualizado")
    if missing:
        print("Jugadores sin datos en el CSV: " + ", ".join(missing), file=sys.stderr)
    if payload["source"]["missing_results"]:
        print(
            f"Resultados pendientes: {len(payload['source']['missing_results'])} filas en {args.results}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
