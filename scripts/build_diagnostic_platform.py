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
    },
    "MDN": {
        "short_name": "Maguindanao del Norte",
        "constraint": "Referral-tier ownership",
        "headline": "Referral assets sit largely outside provincial control.",
        "summary": "The province has the strongest measurement apparatus in the series, but its inpatient stock and referral tier require written access and referral arrangements.",
        "first_instrument": "Publish access and referral arrangements for retained and external beds.",
    },
    "MDS": {
        "short_name": "Maguindanao del Sur",
        "constraint": "Throughput",
        "headline": "The accreditation base is large, but utilization is not measured on the new boundary.",
        "summary": "The province carries substantial accreditation and rural health unit coverage, but the PhilHealth return is not disaggregated after the province split.",
        "first_instrument": "Obtain PhilHealth disaggregation and rebuild the provincial evidence product.",
    },
    "SGA": {
        "short_name": "Special Geographic Area",
        "constraint": "Entitlement",
        "headline": "First-contact sites exist, but payment and legal regimes remain unresolved.",
        "summary": "The area reports service points in every barangay, while dated records show no accreditation line, no public inpatient tier, and unresolved fiscal and licensing regimes.",
        "first_instrument": "Settle fiscal and licensing regimes, then accredit the existing network.",
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
        "body": "The consolidated evidence product carries unresolved data-build issues across all four jurisdictions, and the platform keeps those flags visible.",
        "locator": "BARMM report, finding 3; 90_QA_Flags",
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
    municipalities["coordinate_precision"] = "Municipality representative point"
    for idx, row in municipalities.iterrows():
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
        "qa_flags_open": int(qa_flags["Status"].astype(str).str.contains("Open", case=False, na=False).sum()),
    }
    if totals != {
        "lgus": 84,
        "barangays": 1735,
        "population": 3137511,
        "registered_facilities": 756,
        "rhus_held": 89,
        "rhus_implied": 157,
        "referral_completion_observations": 0,
        "qa_flags_open": totals["qa_flags_open"],
    }:
        raise ValueError(f"Unexpected denominator check: {totals}")

    platform = {
        "metadata": {
            "title": "BARMM Health Systems Diagnostic Atlas",
            "subtitle": "Interactive findings platform for the 2026 BRIGHT-BARMM health-systems diagnostic series.",
            "source_workbook": SOURCE_XLSX.name,
            "source_workbook_url": "https://docs.google.com/spreadsheets/d/1lbx97k43fZVXFIpayd1_vY0BftZ4st9S9_C6sVewYeo/edit",
            "drive_folder_url": "https://drive.google.com/drive/folders/1UpMs323gPKlaMpQ1WvpAKnvM6RL6C9yb",
            "built_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "status_note": "All five reports declare provisional status. Figures are for diagnostic review and should not be used for allocation, procurement, or costing until identified QA flags are closed.",
        },
        "totals": totals,
        "findings": REGIONAL_FINDINGS,
        "sources": records(source_register),
        "jurisdictions": records(jurisdiction_rollup),
        "municipalities": records(municipalities),
        "qa_flags": records(qa_flags),
        "evidence_gaps": records(evidence_gaps),
    }

    (OUTPUT_DIR / "platform_metadata.json").write_text(
        json.dumps(platform["metadata"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    for target in [OUTPUT_DIR / "platform_data.json", DOCS_DATA_DIR / "platform_data.json"]:
        target.write_text(json.dumps(platform, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"Built diagnostic platform data in {OUTPUT_DIR}")
    print(f"Copied GitHub Pages data to {DOCS_DATA_DIR}")


if __name__ == "__main__":
    build()
