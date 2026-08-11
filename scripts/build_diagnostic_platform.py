from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_XLSX = (
    ROOT
    / "barmm_ebdm_pipeline"
    / "data"
    / "input"
    / "diagnostics"
    / "BARMM_Health_Systems_Diagnostics_Consolidated_Data_20260811.xlsx"
)
OUTPUT_DIR = ROOT / "barmm_ebdm_pipeline" / "data" / "output" / "diagnostic_platform"
DOCS_DATA_DIR = ROOT / "docs" / "assets" / "data"
ATLAS_MUNICIPALITIES = ROOT / "barmm_ebdm_pipeline" / "data" / "output" / "facility_dashboard" / "municipalities.csv"
ATLAS_PROVINCES = ROOT / "barmm_ebdm_pipeline" / "data" / "output" / "facility_dashboard" / "provinces.csv"


JURISDICTION_COPY = {
    "LDS": {
        "short_name": "Lanao del Sur",
        "constraint": "Verification",
        "headline": "Readiness cannot yet be verified province-wide.",
        "summary": "The report distinguishes physical access from verified readiness. It identifies where validation and investment should begin, but does not authorize a province-wide construction or procurement envelope.",
        "first_instrument": "Adopt one facility register and verify readiness before capital sizing.",
        "payment_status": "PhilHealth accreditation exists in the wider province, but the workbook does not connect accreditation, benefit use, and charge exposure to each LGU pathway.",
        "record_status": "FHSIS is partially transmitting: 7 of 33 assessed RHUs submit fully on time, 9 submit complete indicator data, and all assessed units carry data-quality issues.",
    },
    "MDN": {
        "short_name": "Maguindanao del Norte",
        "constraint": "Referral-tier ownership",
        "headline": "Referral assets sit largely outside provincial control.",
        "summary": "The province has the strongest measurement apparatus in the series, but its inpatient stock and referral tier require written access and referral arrangements.",
        "first_instrument": "Publish access and referral arrangements for retained and external beds.",
        "payment_status": "The province has accredited institutions, but Konsulta/YAKAP and claims use are not disaggregated to the LGU pathway in the workbook.",
        "record_status": "FHSIS is the strongest among the four areas but still incomplete: 7 of 11 assessed units submit fully on time, and every assessed unit has data-quality issues.",
    },
    "MDS": {
        "short_name": "Maguindanao del Sur",
        "constraint": "Throughput",
        "headline": "The accreditation base is large, but utilization is not measured on the new boundary.",
        "summary": "The province carries substantial accreditation and rural health unit coverage, but the PhilHealth return is not disaggregated after the province split.",
        "first_instrument": "Obtain PhilHealth disaggregation and rebuild the provincial evidence product.",
        "payment_status": "A substantial accreditation base is recorded, but current PhilHealth return and service throughput cannot be computed for the post-split province.",
        "record_status": "FHSIS is partially transmitting: 7 of 22 assessed units submit fully on time, and every assessed unit has data-quality issues.",
    },
    "SGA": {
        "short_name": "Special Geographic Area",
        "constraint": "Entitlement",
        "headline": "First-contact sites exist, but payment and legal regimes remain unresolved.",
        "summary": "The area reports service points in every barangay, while dated records show no accreditation line, no public inpatient tier, and unresolved fiscal and licensing regimes.",
        "first_instrument": "Settle fiscal and licensing regimes, then accredit the existing network.",
        "payment_status": "The dated project record reports no PhilHealth-accredited facilities and no PhilHealth income line for the area; the immediate question is entitlement and accreditation.",
        "record_status": "Routine reporting is not yet a reliable pathway record: only 2 of 8 municipalities were assessed, both had no report, and six were not assessed.",
    },
}


REGIONAL_FINDINGS = [
    {
        "title": "Referral completion is not yet measurable",
        "body": "The consolidated field contains zero recorded referral-completion observations across 57 participating local government units, with missing data elsewhere.",
        "locator": "BARMM report, finding 1; D07 referral domain",
    },
    {
        "title": "Record quality is a shared constraint",
        "body": "Only eight officers are recorded with ICD coding training and only nine of 51 electronic medical-record installations are used for statutory reporting.",
        "locator": "BARMM report, finding 2; D08 FHSIS domain",
    },
    {
        "title": "The pipeline output is not an allocation basis yet",
        "body": "The consolidated evidence product remains provisional across all four jurisdictions; validation must precede allocation, procurement, or costing.",
        "locator": "BARMM report, finding 3; source register status declarations",
    },
    {
        "title": "First contact is a jurisdiction-specific gradient",
        "body": "Registered first-contact coverage ranges from 11.0 percent in Lanao del Sur to 90.5 percent on the SGA national-register basis.",
        "locator": "BARMM report, finding 5; 16_RHU_Standard_and_Coverage",
    },
    {
        "title": "Payment perimeter and throughput do not align",
        "body": "The four jurisdictions hold 229 PhilHealth accreditations, but current throughput cannot be computed for three of the four jurisdictions.",
        "locator": "BARMM report, finding 6; 12_PhilHealth_Accreditation and 13_Konsulta_Return",
    },
    {
        "title": "Inpatient capacity is uneven and ownership-sensitive",
        "body": "The four jurisdictions hold 2,030 acute inpatient beds, or 0.65 per 1,000 residents, with major ownership and concentration differences.",
        "locator": "BARMM report, finding 7; 14_Inpatient_Capacity",
    },
]


SGA_FALLBACK_COORDS = {
    "KADAYANGAN": (7.1229571, 124.4766077),
    "KAPALAWAN": (7.2421239, 124.7911088),
    "LIGAWASAN": (6.9940862, 124.7040135),
    "MALIDEGAO": (7.0607003, 124.6773791),
    "NABALAWAG": (7.1032855, 124.4923617),
    "OLD KAABAKAN": (7.2328881, 124.8447114),
    "PAHAMUDDIN": (7.091, 124.555),
    "TUGUNAN": (7.0451866, 124.6164151),
}

MUNICIPAL_FALLBACK_COORDS = {
    ("LDS", "MARAWICITY"): (8.0047262, 124.2854351),
    ("LDS", "AMAIMANABILANG"): (7.7854607, 124.6821593),
    ("MDS", "SHARIFFAGUAK"): (6.8610172, 124.4444871),
}


def clean_key(value: Any) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.upper().replace("CITY OF ", "")
    return re.sub(r"[^A-Z0-9]+", "", text)


def clean_number(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, float) and math.isfinite(value):
        if value.is_integer():
            return int(value)
        return round(value, 4)
    return value


def count_phrase(value: Any, singular: str, plural: str | None = None) -> str:
    count = clean_number(value) or 0
    label = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {label}"


def sentence_count_phrase(value: Any, singular: str, plural: str | None = None) -> str:
    count = clean_number(value) or 0
    if count == 1:
        return f"One {singular}"
    label = plural or f"{singular}s"
    return f"{count} {label}"


def write_csv(df: pd.DataFrame, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / name, index=False)


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.astype(object).where(pd.notna(df), "").to_dict(orient="records")


def first_not_empty(row: pd.Series, names: list[str]) -> Any:
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return None


def as_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def km_distance(a_lat: Any, a_lon: Any, b_lat: Any, b_lon: Any) -> float | None:
    lat1 = as_float(a_lat)
    lon1 = as_float(a_lon)
    lat2 = as_float(b_lat)
    lon2 = as_float(b_lon)
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return round(2 * radius_km * math.atan2(math.sqrt(h), math.sqrt(1 - h)), 1)


def pathway_condition(row: pd.Series) -> dict[str, str]:
    candidates: list[tuple[float, str, str, str, str]] = []
    philpen = as_float(row.get("PhilPEN %"))
    tb_detection = as_float(row.get("TB detection %"))
    fic = as_float(row.get("FIC %"))
    fbd = as_float(row.get("FBD %"))
    stunting = as_float(row.get("Stunting %"))

    if philpen is not None:
        candidates.append(
            (
                max(0.0, (25.0 - philpen) / 25.0),
                "adult blood-pressure or diabetes risk",
                f"PhilPEN risk assessment is {philpen:.1f}% against the regional monitoring target of 25%.",
                f"{philpen:.1f}% of adults 20+ risk-assessed",
                "PhilPEN screening is a counting signal, not a measured hypertension or diabetes prevalence.",
            )
        )
    if tb_detection is not None:
        candidates.append(
            (
                max(0.0, (40.0 - tb_detection) / 40.0),
                "presumptive tuberculosis",
                f"TB detection is {tb_detection:.1f}% against the two-year monitoring target of 40%.",
                f"{tb_detection:.1f}% TB detection ratio",
                "TB detection is derived from notifications against expected incidence, not a complete case register.",
            )
        )
    if fic is not None:
        candidates.append(
            (
                max(0.0, (90.0 - fic) / 90.0),
                "child fever or vaccine-preventable illness",
                f"Fully immunized child coverage is {fic:.1f}%; low coverage increases the planning relevance of fever and measles pathways.",
                f"{fic:.1f}% fully immunized child coverage",
                "FIC is an administrative coverage signal and can exceed 100% where denominators or returns are inconsistent.",
            )
        )
    if fbd is not None:
        candidates.append(
            (
                max(0.0, (85.0 - fbd) / 85.0),
                "pregnancy or delivery care",
                f"Facility-based delivery is {fbd:.1f}%, so birth-place access remains part of the patient pathway model.",
                f"{fbd:.1f}% facility-based delivery",
                "FBD is a service-coverage signal, not a clinical risk diagnosis.",
            )
        )
    if stunting is not None:
        candidates.append(
            (
                max(0.0, (stunting - 10.0) / 30.0),
                "child undernutrition",
                f"Stunting is {stunting:.1f}%, making child nutrition a visible municipal planning concern.",
                f"{stunting:.1f}% stunting",
                "Stunting is included as a planning signal; it is not an acute consultation diagnosis.",
            )
        )
    if not candidates:
        return {
            "pathway_condition": "unclassified illness",
            "pathway_condition_reason": "No municipal disease-burden indicator is available in the consolidated municipal master.",
            "pathway_counting_metric": "No municipal illness indicator",
            "pathway_condition_caveat": "The reports do not publish LGU-level morbidity rankings.",
        }
    _, condition, reason, metric, caveat = max(candidates, key=lambda item: item[0])
    return {
        "pathway_condition": condition,
        "pathway_condition_reason": reason,
        "pathway_counting_metric": metric,
        "pathway_condition_caveat": caveat,
    }


def first_contact_answer(row: pd.Series) -> str:
    unserved = clean_number(row["unserved_barangays"]) or 0
    opening = (
        f"The current records show {count_phrase(row['first_contact_nodes'], 'place')} for a resident's first health visit: "
        f"{count_phrase(row['Rural health units (as annexed)'], 'Rural Health Unit')} and "
        f"{count_phrase(row['Barangay health stations'], 'Barangay Health Station')}."
    )
    if unserved == 0:
        return (
            f"{opening} Every barangay in this municipal row has a matched first-contact facility in the current records; "
            "local validation should still confirm operating status, staffing, and practical accessibility."
        )
    return (
        f"{opening} {sentence_count_phrase(unserved, 'barangay')} "
        f"{'has' if unserved == 1 else 'have'} no facility matched to "
        f"{'it' if unserved == 1 else 'them'} in the current source layer. Residents may need to use a nearby barangay, outreach services, "
        "or another local arrangement; this must be confirmed locally."
    )


def extract_table_block(sheet: str, marker: str, columns: list[str], width: int) -> pd.DataFrame:
    raw = pd.read_excel(SOURCE_XLSX, sheet_name=sheet, header=None)
    start = raw[raw.iloc[:, 0].astype(str).str.startswith(marker, na=False)].index
    if start.empty:
        return pd.DataFrame(columns=columns)
    header_idx = int(start[0] + 1)
    rows: list[list[Any]] = []
    for idx in range(header_idx + 1, len(raw)):
        row = raw.iloc[idx, :width].tolist()
        if all(pd.isna(cell) for cell in row):
            break
        if isinstance(row[0], str) and row[0].startswith("SOURCE"):
            break
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def build() -> None:
    if not SOURCE_XLSX.exists():
        raise FileNotFoundError(f"Missing source workbook: {SOURCE_XLSX}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    source_register = pd.read_excel(SOURCE_XLSX, sheet_name="01_Source_Register")
    table_index = pd.read_excel(SOURCE_XLSX, sheet_name="03_Table_Index")
    municipal_master = pd.read_excel(SOURCE_XLSX, sheet_name="10_Municipal_Master")
    jurisdiction_rollup = pd.read_excel(SOURCE_XLSX, sheet_name="11_Jurisdiction_Rollup")
    jurisdiction_rollup = jurisdiction_rollup[
        jurisdiction_rollup["Report code"].isin(["LDS", "MDN", "MDS", "SGA", "BARMM"])
    ].copy()
    qa_flags = pd.read_excel(SOURCE_XLSX, sheet_name="90_QA_Flags")
    metadata_dictionary = pd.read_excel(SOURCE_XLSX, sheet_name="91_Metadata_Dictionary")

    evidence_gaps = extract_table_block(
        "D14_Annexes_master_tables_an",
        "TITLE AS PRINTED  ▸  Sixty items",
        ["number", "gap", "why_it_binds", "where_to_obtain"],
        4,
    )

    municipalities = municipal_master[municipal_master["Row type"].eq("LGU")].copy()
    municipalities["municipality_key"] = municipalities["Local government unit"].map(clean_key)
    municipalities["province_key"] = municipalities["Province / area"].map(clean_key)

    atlas_muni = pd.read_csv(ATLAS_MUNICIPALITIES)
    atlas_muni["municipality_key"] = atlas_muni["municipality_city"].map(clean_key)
    atlas_muni["province_key"] = atlas_muni["province"].map(clean_key)
    atlas_muni = atlas_muni[["province_key", "municipality_key", "centroid_lat", "centroid_lon", "psgc_code"]]

    municipalities = municipalities.merge(atlas_muni, on=["province_key", "municipality_key"], how="left")
    municipalities["network_id"] = municipalities["Report"] + "::" + municipalities["municipality_key"]
    municipalities["coordinate_precision"] = "Municipality representative point"
    for idx, row in municipalities.iterrows():
        fallback = MUNICIPAL_FALLBACK_COORDS.get((str(row["Report"]), str(row["municipality_key"])))
        if pd.isna(row["centroid_lat"]) and fallback:
            municipalities.at[idx, "centroid_lat"] = fallback[0]
            municipalities.at[idx, "centroid_lon"] = fallback[1]
            municipalities.at[idx, "coordinate_precision"] = "Public geocoder representative point"
        if pd.isna(row["centroid_lat"]) and row["Report"] == "SGA":
            coords = SGA_FALLBACK_COORDS.get(str(row["Local government unit"]).upper())
            if coords:
                municipalities.at[idx, "centroid_lat"] = coords[0]
                municipalities.at[idx, "centroid_lon"] = coords[1]
                municipalities.at[idx, "coordinate_precision"] = "Public geocoder representative point"
            elif str(row["Local government unit"]).upper() == "PAHAMUDDIN":
                municipalities.at[idx, "coordinate_precision"] = "Area-level fallback point"

    jurisdiction_rollup = jurisdiction_rollup.copy()
    jurisdiction_rollup["short_name"] = jurisdiction_rollup["Report code"].map(
        lambda code: JURISDICTION_COPY.get(str(code), {}).get("short_name", "")
    )
    jurisdiction_rollup["constraint"] = jurisdiction_rollup["Report code"].map(
        lambda code: JURISDICTION_COPY.get(str(code), {}).get("constraint", "")
    )
    jurisdiction_rollup["headline"] = jurisdiction_rollup["Report code"].map(
        lambda code: JURISDICTION_COPY.get(str(code), {}).get("headline", "")
    )
    jurisdiction_rollup["summary"] = jurisdiction_rollup["Report code"].map(
        lambda code: JURISDICTION_COPY.get(str(code), {}).get("summary", "")
    )
    jurisdiction_rollup["first_instrument"] = jurisdiction_rollup["Report code"].map(
        lambda code: JURISDICTION_COPY.get(str(code), {}).get("first_instrument", "")
    )
    jurisdiction_rollup["payment_status"] = jurisdiction_rollup["Report code"].map(
        lambda code: JURISDICTION_COPY.get(str(code), {}).get("payment_status", "")
    )
    jurisdiction_rollup["record_status"] = jurisdiction_rollup["Report code"].map(
        lambda code: JURISDICTION_COPY.get(str(code), {}).get("record_status", "")
    )

    provinces = pd.read_csv(ATLAS_PROVINCES)
    provinces["province_key"] = provinces["province"].map(clean_key)
    jurisdiction_rollup["province_key"] = jurisdiction_rollup["Jurisdiction"].map(clean_key)
    jurisdiction_rollup = jurisdiction_rollup.merge(
        provinces[["province_key", "centroid_lat", "centroid_lon"]],
        on="province_key",
        how="left",
    )
    for idx, row in jurisdiction_rollup.iterrows():
        if row["Report code"] == "SGA" and pd.isna(row["centroid_lat"]):
            jurisdiction_rollup.at[idx, "centroid_lat"] = 7.10
            jurisdiction_rollup.at[idx, "centroid_lon"] = 124.64

    path_parts = municipalities.apply(pathway_condition, axis=1, result_type="expand")
    municipalities = pd.concat([municipalities, path_parts], axis=1)
    municipalities["first_contact_nodes"] = (
        municipalities["Rural health units (as annexed)"].fillna(0)
        + municipalities["Barangay health stations"].fillna(0)
    ).astype(int)
    municipalities["unserved_barangays"] = municipalities[
        "Barangays without a first-contact facility (as annexed)"
    ].copy()
    missing_unserved = municipalities["unserved_barangays"].isna()
    municipalities.loc[missing_unserved, "unserved_barangays"] = (
        municipalities.loc[missing_unserved, "Barangays (as annexed)"].fillna(0)
        - municipalities.loc[missing_unserved, "LIVE  Barangays with a facility"].fillna(0)
    )
    municipalities["unserved_barangays"] = municipalities["unserved_barangays"].clip(lower=0)
    municipalities["first_contact_answer"] = municipalities.apply(first_contact_answer, axis=1)

    hub_rows = municipalities[
        municipalities["Hospitals"].fillna(0).astype(float).gt(0)
        & municipalities["centroid_lat"].notna()
        & municipalities["centroid_lon"].notna()
    ].copy()
    for idx, row in municipalities.iterrows():
        same_jurisdiction = hub_rows[hub_rows["Report"].eq(row["Report"])]
        candidate_hubs = same_jurisdiction if not same_jurisdiction.empty else hub_rows
        best: dict[str, Any] | None = None
        for _, hub in candidate_hubs.iterrows():
            distance = km_distance(row["centroid_lat"], row["centroid_lon"], hub["centroid_lat"], hub["centroid_lon"])
            if distance is None:
                continue
            if best is None or distance < best["distance"]:
                best = {
                    "id": hub["network_id"],
                    "name": hub["Local government unit"],
                    "report": hub["Report"],
                    "distance": distance,
                    "local": hub["network_id"] == row["network_id"],
                }
        if best:
            municipalities.at[idx, "nearest_referral_id"] = best["id"]
            municipalities.at[idx, "nearest_referral_lgu"] = best["name"]
            municipalities.at[idx, "nearest_referral_report"] = best["report"]
            municipalities.at[idx, "nearest_referral_distance_km"] = best["distance"]
            municipalities.at[idx, "referral_answer"] = (
                "If the case needs inpatient care, the municipal row records a local hospital or inpatient receiving point. This does not confirm licensure, referral protocol, or actual admission."
                if best["local"]
                else f"If the case needs care beyond first contact, the closest mapped municipality with a recorded hospital is {best['name']}, about {best['distance']} km away by straight-line representative distance. This is not a travel-time route and must be checked against the local referral network."
            )
        else:
            municipalities.at[idx, "referral_answer"] = "No mapped referral hub could be computed from available representative coordinates."

    jurisdiction_status = {
        row["Report code"]: {
            "payment_status": row.get("payment_status", ""),
            "record_status": row.get("record_status", ""),
        }
        for _, row in jurisdiction_rollup.iterrows()
    }
    municipalities["payment_answer"] = municipalities["Report"].map(
        lambda code: jurisdiction_status.get(code, {}).get("payment_status", "Payment status is not measured for this LGU pathway.")
    )
    municipalities["record_answer"] = municipalities["Report"].map(
        lambda code: jurisdiction_status.get(code, {}).get("record_status", "Record feedback is not measured for this LGU pathway.")
    )
    municipalities["referral_completion_answer"] = (
        "No referral-completion observations are recorded in the consolidated regional workbook; the pathway cannot confirm arrival or feedback."
    )

    write_csv(source_register, "source_register.csv")
    write_csv(jurisdiction_rollup, "jurisdiction_rollup.csv")
    write_csv(municipalities, "municipal_master.csv")
    write_csv(qa_flags, "qa_flags.csv")
    write_csv(evidence_gaps, "evidence_gaps.csv")
    write_csv(table_index, "table_index.csv")
    write_csv(metadata_dictionary, "metadata_dictionary.csv")

    regional = jurisdiction_rollup[jurisdiction_rollup["Report code"].isin(["LDS", "MDN", "MDS", "SGA"])]
    totals = {
        "lgus": int(regional["Population 2024 as printed"].shape[0] and 84),
        "barangays": int(regional["LIVE  Sum of LGU rows.1"].sum()),
        "population": int(regional["LIVE  Sum of LGU rows"].sum()),
        "registered_facilities": 756,
        "rhus_held": int(regional["LIVE  Sum of LGU rows.2"].sum()),
        "rhus_implied": int(regional["RHUs implied as printed (Regional Table 4)"].sum()),
        "referral_completion_observations": 0,
    }
    if totals != {
        "lgus": 84,
        "barangays": 1735,
        "population": 3137511,
        "registered_facilities": 756,
        "rhus_held": 89,
        "rhus_implied": 157,
        "referral_completion_observations": 0,
    }:
        raise ValueError(f"Unexpected denominator check: {totals}")

    platform = {
        "metadata": {
            "title": "BARMM Health Atlas",
            "subtitle": "Evidence for UHC action in four priority jurisdictions",
            "source_workbook": SOURCE_XLSX.name,
            "source_workbook_url": "https://docs.google.com/spreadsheets/d/1lbx97k43fZVXFIpayd1_vY0BftZ4st9S9_C6sVewYeo/edit",
            "drive_folder_url": "https://drive.google.com/drive/folders/1UpMs323gPKlaMpQ1WvpAKnvM6RL6C9yb",
            "built_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "status_note": "Evidence status: provisional baseline. Figures are for diagnostic review and UHC action planning; they should not be used for allocation, procurement, or costing until validation is complete.",
        },
        "totals": totals,
        "findings": REGIONAL_FINDINGS,
        "sources": records(source_register),
        "jurisdictions": records(jurisdiction_rollup),
        "municipalities": records(municipalities),
        "qa_flags": records(qa_flags),
        "evidence_gaps": records(evidence_gaps),
    }
    public_platform = {
        key: value
        for key, value in platform.items()
        if key not in {"qa_flags", "evidence_gaps"}
    }

    (OUTPUT_DIR / "platform_metadata.json").write_text(
        json.dumps(platform["metadata"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "platform_data.json").write_text(
        json.dumps(platform, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (DOCS_DATA_DIR / "platform_data.json").write_text(
        json.dumps(public_platform, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    print(f"Built diagnostic platform data in {OUTPUT_DIR}")
    print(f"Copied GitHub Pages data to {DOCS_DATA_DIR}")


if __name__ == "__main__":
    build()
