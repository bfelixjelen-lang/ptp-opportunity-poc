import pandas as pd
import streamlit as st
from pathlib import Path
import re

st.set_page_config(page_title="Pathways to Purpose Opportunity Guide", layout="wide")

st.title("Pathways to Purpose Opportunity Guide")
st.caption(
    "Proof of concept using approved Mercer opportunity records enriched from CRM, "
    "catalog, and public program sources."
)

BASE_DIR = Path(__file__).parent

# Keep the CSV name stable for Streamlit/GitHub deployment.
# If you later choose to deploy the Excel version, add openpyxl to requirements.txt.
csv_path = BASE_DIR / "ptp_opportunities.csv"
xlsx_path = BASE_DIR / "PtP Opportunity POC Database Enriched.xlsx"


@st.cache_data
def load_data():
    """Load approved opportunity records from CSV first, then Excel as fallback."""
    if csv_path.exists():
        df = pd.read_csv(csv_path)
    elif xlsx_path.exists():
        df = pd.read_excel(xlsx_path, sheet_name="PtP Opportunity POC Database")
    else:
        st.error(
            "No opportunity data file found. Place 'ptp_opportunities.csv' or "
            "'PtP Opportunity POC Database Enriched.xlsx' next to app.py."
        )
        st.stop()

    df.columns = [str(c).strip() for c in df.columns]

    required = [
        "id",
        "opportunity_name",
        "country_region",
        "gic_site",
        "program_type",
        "disciplines",
        "student_year",
        "term_timing",
        "language_needed",
        "cost_range",
        "description",
        "eligibility",
        "student_next_step",
        "contact",
        "status",
        "keywords",
        "public_notes",
    ]

    optional = [
        "host_unit",
        "academic_year",
        "active_years_combined",
        "faculty_contacts",
        "minimum_gpa",
        "course_codes",
        "course_titles",
        "credits",
        "public_program_url",
        "academic_themes",
        "course_description_summary",
        "course_prerequisites_summary",
        "course_frequency_summary",
        "catalog_source_detail",
        "data_confidence",
        "source_file",
    ]

    for col in required + optional:
        if col not in df.columns:
            df[col] = ""

    df = df[df["status"].fillna("").astype(str).str.lower() == "approved"].copy()
    return df


df = load_data()


def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value)


def lower_text(value):
    return safe_text(value).lower()


def combined_text(row):
    fields = [
        "opportunity_name",
        "country_region",
        "gic_site",
        "program_type",
        "disciplines",
        "student_year",
        "term_timing",
        "language_needed",
        "description",
        "eligibility",
        "keywords",
        "public_notes",
        "host_unit",
        "faculty_contacts",
        "course_codes",
        "course_titles",
        "academic_themes",
        "course_description_summary",
        "course_prerequisites_summary",
    ]
    return " ".join(lower_text(row.get(field, "")) for field in fields)


def extract_terms(text, min_length=4):
    """Simple keyword extraction for the non-AI matching prototype."""
    if not text:
        return []

    raw_terms = (
        str(text)
        .lower()
        .replace(",", " ")
        .replace("/", " ")
        .replace("-", " ")
        .split()
    )

    terms = []
    for term in raw_terms:
        clean = term.strip(".,!?;:()[]{}'\"").lower()
        if len(clean) >= min_length:
            terms.append(clean)

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(terms))


st.sidebar.header("Explore Opportunities")

region_options = sorted(
    [x for x in df["country_region"].dropna().astype(str).unique() if x.strip()]
)

type_options = sorted(
    [x for x in df["program_type"].dropna().astype(str).unique() if x.strip()]
)

theme_options = sorted(
    set(
        theme.strip()
        for value in df["academic_themes"].dropna().astype(str)
        for theme in value.replace("|", ";").split(";")
        if theme.strip()
    )
)

region = st.sidebar.multiselect("Country / Region", region_options)
program_type = st.sidebar.multiselect("Program Type", type_options)
academic_theme = st.sidebar.multiselect("Academic Theme", theme_options)
discipline_search = st.sidebar.text_input("Discipline or keyword", "")

filtered = df.copy()

if region:
    filtered = filtered[filtered["country_region"].isin(region)]

if program_type:
    filtered = filtered[filtered["program_type"].isin(program_type)]

if academic_theme:
    pattern = "|".join(re.escape(t) for t in academic_theme)
    filtered = filtered[
        filtered["academic_themes"].astype(str).str.contains(
            pattern, case=False, na=False, regex=True
        )
    ]

if discipline_search:
    mask = pd.Series(False, index=filtered.index)
    for col in [
        "disciplines",
        "keywords",
        "academic_themes",
        "description",
        "course_titles",
        "course_description_summary",
    ]:
        mask = mask | filtered[col].astype(str).str.contains(
            discipline_search, case=False, na=False, regex=False
        )
    filtered = filtered[mask]


st.header("Match Me")
st.caption(
    "Start with a plain-language description. Use optional filters only if you want "
    "to narrow the results."
)

student_profile_input = st.text_area(
    "Tell us about yourself and what you are looking for:",
    placeholder=(
        "Example: I am a second-year engineering student. "
        "I want to go to Latin America and do service, research, or sustainability work."
    ),
    height=140,
)

with st.expander("Optional: add more detail"):
    col1, col2 = st.columns(2)

    with col1:
        student_year_input = st.selectbox(
            "What year are you?",
            [
                "",
                "First-year",
                "Second-year",
                "Third-year",
                "Fourth-year",
                "Graduate/Professional",
            ],
        )
        discipline_input = st.text_input(
            "Major or academic interest",
            placeholder="Example: Engineering, Public Health, Education, Political Science",
        )

    with col2:
        region_input = st.text_input(
            "Region or country interest",
            placeholder="Example: Dominican Republic, Latin America, Korea, Europe",
        )
        program_interest_input = st.multiselect(
            "Opportunity type",
            [
                "Study Abroad",
                "Exchange Program",
                "Faculty-Led Program",
                "Mercer On Mission",
                "Internship",
                "Research",
                "Service",
                "Graduate Study",
                "Employment",
            ],
        )

    goal_input = st.text_area(
        "Additional goals or constraints",
        placeholder=(
            "Example: I care about cost, language, timing, public health, internships, "
            "or graduate school."
        ),
        height=90,
    )


def score_and_explain(row):
    score = 0
    reasons = []
    opportunity_text = combined_text(row)

    # 1. Open-ended natural language match.
    profile_terms = extract_terms(student_profile_input, min_length=4)
    profile_hits = [term for term in profile_terms if term in opportunity_text]

    if profile_hits:
        score += min(len(profile_hits), 10)
        reasons.append("matches details from your open-ended profile")

    # 2. Student year boost.
    if student_year_input and student_year_input.lower() in opportunity_text:
        score += 2
        reasons.append(f"matches your student year ({student_year_input})")

    # 3. Academic interest boost.
    if discipline_input:
        discipline_terms = extract_terms(discipline_input, min_length=3)
        if any(term in opportunity_text for term in discipline_terms):
            score += 4
            reasons.append("connects to your academic interest")

    # 4. Region/country boost.
    if region_input:
        region_terms = extract_terms(region_input, min_length=3)
        if any(term in opportunity_text for term in region_terms):
            score += 4
            reasons.append("matches your regional interest")

    # 5. Program type boost.
    if program_interest_input:
        hits = [
            interest
            for interest in program_interest_input
            if interest.lower() in opportunity_text
        ]
        if hits:
            score += 3
            reasons.append("matches your preferred opportunity type")

    # 6. Additional goals boost.
    if goal_input:
        goal_terms = extract_terms(goal_input, min_length=4)
        goal_hits = [term for term in goal_terms if term in opportunity_text]
        if goal_hits:
            score += min(len(goal_hits), 6)
            reasons.append("connects to your stated goals or constraints")

    if not reasons:
        reasons.append("may be worth exploring, but the fit is general")

    return score, reasons


def show_opportunity(row, include_score=False):
    with st.container(border=True):
        st.markdown(f"### {safe_text(row['opportunity_name'])}")

        if include_score:
            st.write(f"**Match Score:** {safe_text(row.get('match_score', ''))}")
            st.write(
                "**Why this may fit:** "
                + "; ".join(row.get("match_reasons", []))
                + "."
            )

        st.write(f"**Region:** {safe_text(row['country_region'])}")
        st.write(f"**Site:** {safe_text(row['gic_site'])}")
        st.write(f"**Program Type:** {safe_text(row['program_type'])}")
        st.write(f"**Host Unit:** {safe_text(row.get('host_unit', ''))}")
        st.write(f"**Disciplines:** {safe_text(row['disciplines'])}")
        st.write(f"**Themes:** {safe_text(row.get('academic_themes', ''))}")
        st.write(f"**Timing:** {safe_text(row['term_timing'])}")
        st.write(safe_text(row["description"]))

        if safe_text(row.get("course_titles", "")):
            st.write(f"**Associated Courses:** {safe_text(row.get('course_titles', ''))}")

        if safe_text(row.get("credits", "")):
            st.write(f"**Credits:** {safe_text(row.get('credits', ''))}")

        st.write(f"**Eligibility:** {safe_text(row['eligibility'])}")

        if safe_text(row.get("course_prerequisites_summary", "")):
            st.write(
                f"**Catalog Prerequisites:** "
                f"{safe_text(row.get('course_prerequisites_summary', ''))}"
            )

        st.write(f"**Next Step:** {safe_text(row['student_next_step'])}")
        st.write(f"**Contact:** {safe_text(row['contact'])}")

        url = safe_text(row.get("public_program_url", ""))
        if url.startswith("http"):
            st.link_button("Open Public Program Page", url)

        with st.expander("Source and catalog notes"):
            st.write(f"**Data confidence:** {safe_text(row.get('data_confidence', ''))}")
            st.write(
                f"**Catalog source:** {safe_text(row.get('catalog_source_detail', ''))}"
            )
            st.write(f"**Source file:** {safe_text(row.get('source_file', ''))}")
            st.write(safe_text(row.get("public_notes", "")))


has_match_input = any(
    [
        student_profile_input,
        student_year_input,
        discipline_input,
        region_input,
        program_interest_input,
        goal_input,
    ]
)

if has_match_input:
    ranked = df.copy()
    ranked[["match_score", "match_reasons"]] = ranked.apply(
        lambda row: pd.Series(score_and_explain(row)), axis=1
    )
    ranked = ranked.sort_values("match_score", ascending=False)

    if ranked["match_score"].max() > 0:
        ranked = ranked[ranked["match_score"] > 0].head(5)
    else:
        ranked = ranked.head(5)

    st.subheader("Recommended Opportunities")
    for _, row in ranked.iterrows():
        show_opportunity(row, include_score=True)

    st.info(
        "This proof of concept recommends approved opportunities only. Final eligibility, "
        "cost, credit, financial aid, and travel approval must be confirmed with Mercer staff."
    )
else:
    st.info("Answer one or more questions above to generate recommendations.")


st.header("Browse Approved Opportunities")
st.caption(f"{len(filtered)} approved opportunities match the current filters.")

for _, row in filtered.iterrows():
    show_opportunity(row, include_score=False)
