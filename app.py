import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Pathways to Purpose Opportunity Guide", layout="wide")

st.title("Pathways to Purpose Opportunity Guide")
st.caption("Proof of concept using public/demo opportunity records only.")

csv_path = Path(__file__).parent / "ptp_opportunities.csv"
df = pd.read_csv(csv_path)
df = df[df["status"].str.lower() == "approved"]

st.sidebar.header("Explore Opportunities")

region = st.sidebar.multiselect(
    "Country / Region",
    sorted(df["country_region"].dropna().unique())
)

program_type = st.sidebar.multiselect(
    "Program Type",
    sorted(df["program_type"].dropna().unique())
)

discipline_search = st.sidebar.text_input("Discipline keyword", "")

filtered = df.copy()
st.header("Match Me")

st.caption(
    "Answer a few questions and the guide will recommend approved opportunities from the demo database."
)

col1, col2 = st.columns(2)

with col1:
    student_year_input = st.selectbox(
        "What year are you?",
        ["", "First-year", "Second-year", "Third-year", "Fourth-year", "Graduate/Professional"]
    )

    discipline_input = st.text_input(
        "What is your major or academic interest?",
        placeholder="Example: Engineering, Public Health, Education, Political Science"
    )

with col2:
    region_input = st.text_input(
        "Where are you interested in going?",
        placeholder="Example: Dominican Republic, Latin America, Korea, Europe"
    )

    program_interest_input = st.multiselect(
        "What kind of opportunity are you looking for?",
        ["Study Abroad", "Mercer On Mission", "Internship", "Research", "Service", "Employment", "Graduate Study"]
    )

goal_input = st.text_area(
    "What do you want to do or explore?",
    placeholder="Example: I want to work on sustainability, public health, service, language, internships, or research.",
    height=100
)

def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value).lower()

def score_and_explain(row):
    score = 0
    reasons = []

    opportunity_text = " ".join([
        safe_text(row.get("opportunity_name", "")),
        safe_text(row.get("country_region", "")),
        safe_text(row.get("gic_site", "")),
        safe_text(row.get("program_type", "")),
        safe_text(row.get("disciplines", "")),
        safe_text(row.get("student_year", "")),
        safe_text(row.get("term_timing", "")),
        safe_text(row.get("language_needed", "")),
        safe_text(row.get("description", "")),
        safe_text(row.get("eligibility", "")),
        safe_text(row.get("keywords", "")),
        safe_text(row.get("public_notes", "")),
    ])

    if student_year_input and student_year_input.lower() in opportunity_text:
        score += 2
        reasons.append(f"matches your student year ({student_year_input})")

    if discipline_input:
        discipline_terms = [term.strip().lower() for term in discipline_input.replace(",", " ").split()]
        discipline_hits = [term for term in discipline_terms if len(term) > 3 and term in opportunity_text]
        if discipline_hits:
            score += 4
            reasons.append("connects to your academic interest")

    if region_input:
        region_terms = [term.strip().lower() for term in region_input.replace(",", " ").split()]
        region_hits = [term for term in region_terms if len(term) > 3 and term in opportunity_text]
        if region_hits:
            score += 4
            reasons.append("matches your regional interest")

    if program_interest_input:
        program_hits = []
        for interest in program_interest_input:
            if interest.lower() in opportunity_text:
                program_hits.append(interest)
        if program_hits:
            score += 3
            reasons.append("matches your preferred opportunity type")

    if goal_input:
        goal_terms = [term.strip().lower() for term in goal_input.replace(",", " ").split()]
        goal_hits = [term for term in goal_terms if len(term) > 4 and term in opportunity_text]
        if goal_hits:
            score += min(len(goal_hits), 5)
            reasons.append("connects to your stated goals")

    if not reasons:
        reasons.append("may be worth exploring, but the fit is general")

    return score, reasons

if student_year_input or discipline_input or region_input or program_interest_input or goal_input:
    ranked = df.copy()
    ranked[["match_score", "match_reasons"]] = ranked.apply(
        lambda row: pd.Series(score_and_explain(row)),
        axis=1
    )

    ranked = ranked.sort_values("match_score", ascending=False).head(5)

    st.subheader("Recommended Opportunities")

    for _, row in ranked.iterrows():
        with st.container(border=True):
            st.markdown(f"### {row['opportunity_name']}")
            st.write(f"**Match Score:** {row['match_score']}")
            st.write("**Why this may fit:** " + "; ".join(row["match_reasons"]) + ".")
            st.write(f"**Region:** {row['country_region']}")
            st.write(f"**GIC Site:** {row['gic_site']}")
            st.write(f"**Program Type:** {row['program_type']}")
            st.write(f"**Disciplines:** {row['disciplines']}")
            st.write(f"**Timing:** {row['term_timing']}")
            st.write(row["description"])
            st.write(f"**Eligibility:** {row['eligibility']}")
            st.write(f"**Next Step:** {row['student_next_step']}")
            st.write(f"**Contact:** {row['contact']}")

    st.info(
        "This proof of concept recommends approved demo opportunities only. Final eligibility, cost, credit, financial aid, and travel approval must be confirmed with Mercer staff."
    )
else:
    st.info("Answer one or more questions above to generate recommendations.")

if region:
    filtered = filtered[filtered["country_region"].isin(region)]

if program_type:
    filtered = filtered[filtered["program_type"].isin(program_type)]

if discipline_search:
    filtered = filtered[
        filtered["disciplines"].str.contains(discipline_search, case=False, na=False)
        | filtered["keywords"].str.contains(discipline_search, case=False, na=False)
    ]

st.header("Match Me")

student_profile = st.text_area(
    "Tell us about yourself:",
    placeholder="Example: I am a second-year engineering student. I want to go to Latin America. I want research or service related to public health or sustainability.",
    height=120
)

def score_row(row, profile):
    profile = profile.lower()
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
    ]
    text = " ".join(str(row.get(field, "")) for field in fields).lower()
    score = 0
    for word in profile.split():
        clean = word.strip(".,!?;:()[]{}").lower()
        if len(clean) > 3 and clean in text:
            score += 1
    return score

if student_profile:
    ranked = df.copy()
    ranked["match_score"] = ranked.apply(lambda row: score_row(row, student_profile), axis=1)
    ranked = ranked.sort_values("match_score", ascending=False).head(5)

    st.subheader("Recommended Opportunities")

    for _, row in ranked.iterrows():
        with st.container(border=True):
            st.markdown(f"### {row['opportunity_name']}")
            st.write(f"**Region:** {row['country_region']}")
            st.write(f"**GIC Site:** {row['gic_site']}")
            st.write(f"**Program Type:** {row['program_type']}")
            st.write(f"**Disciplines:** {row['disciplines']}")
            st.write(f"**Timing:** {row['term_timing']}")
            st.write(row["description"])
            st.write(f"**Eligibility:** {row['eligibility']}")
            st.write(f"**Next Step:** {row['student_next_step']}")
            st.write(f"**Contact:** {row['contact']}")
else:
    st.info("Enter a student profile above to generate recommendations.")

st.header("Browse Approved Opportunities")

for _, row in filtered.iterrows():
    with st.container(border=True):
        st.markdown(f"### {row['opportunity_name']}")
        st.write(f"**Region:** {row['country_region']}")
        st.write(f"**Program Type:** {row['program_type']}")
        st.write(f"**Disciplines:** {row['disciplines']}")
        st.write(row["description"])
        st.write(f"**Next Step:** {row['student_next_step']}")