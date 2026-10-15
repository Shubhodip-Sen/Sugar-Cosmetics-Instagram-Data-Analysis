
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Sugar Cosmetics | Instagram Insights", page_icon="💄", layout="wide")
PINK, BLACK = "#E6007E", "#1A1A1A"
HERE = Path(__file__).parent
CANDIDATES = [
    HERE / "data" / "sugar_instagram_clean.csv",
    HERE / "data" / "sugar_instagram_clean.xlsx",
    HERE / "sugar_instagram_clean.csv",
    HERE / "sugar_instagram_clean.xlsx",
    HERE / "data" / "sugar_cosmetics_instagram_data.xlsx",
    HERE / "sugar_cosmetics_instagram_data.xlsx",
]
WEEK = ["Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday"]


def prepare(d):
    """Accepts the raw or the cleaned file and adds any missing derived columns."""
    d = d.copy()
    d.columns = [c.strip().replace(" ", "_").lower() for c in d.columns]
    d["post_date"] = pd.to_datetime(d["post_date"])
    d = d.drop_duplicates().dropna().sort_values("post_date").reset_index(drop=True)
    if "post_id" not in d:
        d.insert(0, "post_id", range(1, len(d) + 1))
    d["month"] = d.post_date.dt.to_period("M").astype(str)
    d["weekday"] = d.post_date.dt.day_name()
    d["interactions"] = d.likes + d.comments + d.shares + d.saves
    d["engagement_rate_pct"] = d.interactions / d.reach * 100
    d["hashtag_count"] = d.hashtags.str.count(",") + 1
    d["post_label"] = ("#" + d.post_id.astype(str) + " · " + d.post_type + " · " + d.campaign_type
                       + " · " + d.post_date.dt.strftime("%d %b %y"))
    d["tag_list"] = d["hashtags"].str.split(r",\s*", regex=True)
    return d


def read_any(src):
    name = getattr(src, "name", str(src)).lower()
    if name.endswith(".csv"):
        return pd.read_csv(src)
    return pd.read_excel(src, sheet_name=0)   # first sheet = posts


@st.cache_data
def load_path(path):
    return prepare(read_any(path))


path = next((p for p in CANDIDATES if p.exists()), None)
if path is not None:
    df = load_path(str(path))
else:
    st.title("💄 Sugar Cosmetics — Instagram Performance Dashboard")
    st.warning("Data file not found next to app.py. Put `sugar_instagram_clean.csv` (or the original "
               "`sugar_cosmetics_instagram_data.xlsx`) in this folder or in a `data/` subfolder — or upload it below.")
    up = st.file_uploader(
        "Upload the cleaned CSV/XLSX or the raw Excel file", type=["csv", "xlsx"])
    if up is None:
        st.stop()
    df = prepare(read_any(up))

# ---------------- Sidebar filters ----------------
st.sidebar.title("Filters")
types = st.sidebar.multiselect("Post type", sorted(
    df.post_type.unique()), default=sorted(df.post_type.unique()))
camps = st.sidebar.multiselect("Campaign type", sorted(
    df.campaign_type.unique()), default=sorted(df.campaign_type.unique()))
months = st.sidebar.multiselect("Month", sorted(
    df.month.unique()), default=sorted(df.month.unique()))
all_tags = sorted({t for l in df.tag_list for t in l})
tags = st.sidebar.multiselect(
    "Hashtag (post contains any)", all_tags, default=all_tags)

f = df[df.post_type.isin(types) & df.campaign_type.isin(
    camps) & df.month.isin(months)]
f = f[f.tag_list.apply(lambda l: any(t in tags for t in l))]
if f.empty:
    st.warning("No posts match the selected filters.")
    st.stop()

st.title("💄 Sugar Cosmetics — Instagram Performance Dashboard")
st.caption(
    f"{f.post_date.min():%d %b %Y} → {f.post_date.max():%d %b %Y} · {len(f):,} posts after filters")

# ---------------- KPIs ----------------
c = st.columns(6)
c[0].metric("Total posts", f"{len(f):,}")
c[1].metric("Total likes", f"{f.likes.sum()/1e6:,.1f}M")
c[2].metric("Total comments", f"{f.comments.sum()/1e6:,.2f}M")
c[3].metric("Total reach", f"{f.reach.sum()/1e6:,.1f}M")
c[4].metric("Avg engagement rate", f"{f.engagement_rate_pct.mean():.2f}%")
c[5].metric("Profile visit → follow",
            f"{f.follows.sum()/f.profile_visits.sum()*100:.1f}%")
st.caption("Engagement rate = (likes + comments + shares + saves) ÷ reach × 100")


def style(fig, h=380):
    fig.update_layout(height=h, margin=dict(
        l=10, r=10, t=50, b=10), template="simple_white")
    return fig


tabs = st.tabs(["Trend", "Top posts", "Post type", "Weekday",
               "Funnel", "Hashtags", "Campaign & source", "Growth", "Strategy"])

with tabs[0]:
    m = f.groupby("month").size().reset_index(name="posts")
    st.plotly_chart(style(px.line(m, x="month", y="posts", markers=True,
                    title="Posts per month", color_discrete_sequence=[PINK])), width="stretch")
    st.info(
        "Apr-2024 and Apr-2025 are partial months (data runs 19 Apr 2024 – 19 Apr 2025).")

with tabs[1]:
    a, b = st.columns(2)
    t1 = f.nlargest(10, "likes").sort_values("likes")
    a.plotly_chart(style(px.bar(t1, x="likes", y="post_label", orientation="h",
                   title="Top 10 posts by likes", color_discrete_sequence=[PINK])), width="stretch")
    t2 = f.nlargest(10, "engagement_rate_pct").sort_values(
        "engagement_rate_pct")
    b.plotly_chart(style(px.bar(t2, x="engagement_rate_pct", y="post_label", orientation="h",
                   title="Top 10 posts by engagement rate (%)", color_discrete_sequence=[BLACK])), width="stretch")
    st.dataframe(t2[["post_label", "likes", "reach", "engagement_rate_pct",
                 "hashtags"]].iloc[::-1], hide_index=True, width="stretch")

with tabs[2]:
    g = f.groupby("post_type")[["likes", "comments", "shares", "saves"]].mean(
    ).reset_index().melt("post_type", var_name="metric", value_name="avg")
    st.plotly_chart(style(px.bar(g, x="post_type", y="avg", color="metric", barmode="group", title="Average per post by type", log_y=True,
                                 color_discrete_sequence=[PINK, BLACK, "#BDBDBD", "#F7A8D0"])), width="stretch")
    e = f.groupby("post_type").engagement_rate_pct.mean().reset_index()
    st.plotly_chart(style(px.bar(e, x="post_type", y="engagement_rate_pct",
                    title="Avg engagement rate (%) by type", color_discrete_sequence=[PINK]), 300), width="stretch")

with tabs[3]:
    w = f.groupby("weekday").engagement_rate_pct.mean().reindex(
        WEEK).reset_index()
    fig = px.bar(w, x="weekday", y="engagement_rate_pct",
                 title="Avg engagement rate (%) by weekday", color_discrete_sequence=[PINK])
    fig.update_yaxes(range=[w.engagement_rate_pct.min()
                     * 0.98, w.engagement_rate_pct.max() * 1.005])
    st.plotly_chart(style(fig), width="stretch")
    st.caption(
        "Y-axis is truncated to make small differences visible — the spread is under 0.25 percentage points.")

with tabs[4]:
    vals = [f.impressions.sum(), f.reach.sum(), f.likes.sum(),
            f.comments.sum(), f.shares.sum(), f.saves.sum()]
    st.plotly_chart(style(go.Figure(go.Funnel(y=["Impressions", "Reach", "Likes", "Comments", "Shares", "Saves"], x=vals,
                                              marker=dict(
                                                  color=[BLACK, "#555", PINK, "#F04FA3", "#F7A8D0", "#FBD3E7"]),
                                              textinfo="value+percent previous")).update_layout(title="Engagement funnel"), 460), width="stretch")
    st.caption("Likes, comments, shares and saves are parallel actions on a post, so the 'drop-off' between them is a mix, not a sequence.")

with tabs[5]:
    ex = f.explode("tag_list").groupby("tag_list").agg(posts=("post_id", "size"), er=(
        "engagement_rate_pct", "mean"), reach=("reach", "mean")).reset_index()
    a, b = st.columns(2)
    fig = px.bar(ex.sort_values("er"), x="er", y="tag_list", orientation="h",
                 title="Avg engagement rate (%) by hashtag", color_discrete_sequence=[PINK])
    fig.update_xaxes(range=[ex.er.min() * 0.98, ex.er.max() * 1.003])
    a.plotly_chart(style(fig), width="stretch")
    b.plotly_chart(style(px.pie(ex, names="tag_list", values="posts", title="Hashtag usage share",
                   color_discrete_sequence=px.colors.sequential.RdPu)), width="stretch")
    n = f.groupby("hashtag_count").engagement_rate_pct.mean().reset_index()
    st.plotly_chart(style(px.bar(n, x="hashtag_count", y="engagement_rate_pct",
                    title="Avg engagement rate (%) by number of hashtags", color_discrete_sequence=[BLACK]), 300), width="stretch")

with tabs[6]:
    a, b = st.columns(2)
    cp = f.groupby("campaign_type").agg(reach=("reach", "mean"), likes=(
        "likes", "mean"), er=("engagement_rate_pct", "mean")).reset_index()
    a.plotly_chart(style(px.bar(cp, x="campaign_type", y="reach",
                   title="Avg reach per post by campaign", color_discrete_sequence=[PINK])), width="stretch")
    so = f.groupby("engagement_source").agg(reach=("reach", "mean"),
                                            er=("engagement_rate_pct", "mean")).reset_index()
    b.plotly_chart(style(px.bar(so, x="engagement_source", y="reach",
                   title="Avg reach per post by source", color_discrete_sequence=[BLACK])), width="stretch")
    st.dataframe(cp.round(2), hide_index=True, width="stretch")

with tabs[7]:
    g = f.groupby("month").agg(follows=("follows", "sum"),
                               visits=("profile_visits", "sum")).reset_index()
    g["conv"] = g.follows / g.visits * 100
    st.plotly_chart(style(px.line(g, x="month", y="follows", markers=True,
                    title="Follows generated per month", color_discrete_sequence=[PINK])), width="stretch")
    st.plotly_chart(style(px.line(g, x="month", y="conv", markers=True,
                    title="Profile visit → follow conversion (%)", color_discrete_sequence=[BLACK]), 300), width="stretch")
    st.caption("No follower-count column exists, so growth is proxied by follows generated. Partial months (Apr-24, Apr-25) will look low.")

with tabs[8]:
    st.subheader("Key takeaways")
    st.markdown("""
- **Account is healthy but uniform:** ~18.5% average engagement rate; every format, weekday, campaign and hashtag lands within ~0.5 pp of the average.
- **No segment is statistically 'best'** (ANOVA p > 0.05 for format, weekday, campaign, source, emotion) — don't over-rotate budget based on tiny gaps.
- **Organic reach (≈19,970/post) is highest** — paid posts are not buying extra reach.
- **Stories lag on follows** (≈175/post vs ≈179 for Image) and **Festive Offer posts have the lowest reach** (≈19,506).
- **Tutorials convert best** from profile visit to follow (≈30.0%).
- **Next step:** A/B test within one variable at a time and track cost per follow.
""")
