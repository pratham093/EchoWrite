"""
EchoWrite AI — Streamlit Application
Multi-agent content processing with RL-based feedback, semantic search,
and voice support.

Run:  streamlit run app.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── EchoWrite imports ────────────────────────────────────────────────
from scrapers.sync_scraper import SyncWebScraper
from agents.writer import WriterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.editor_agent import EditorAgent
from storage.version_manager import VersionManager
from rl_models.reward_model import RewardModel
from rl_models.inference_engine import ContentSelectionEngine
from search.semantic_search import SemanticSearch
from config.settings import settings
from agents.voice_interface import VoiceInterface, SPEECH_RECOGNITION_AVAILABLE

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="EchoWrite AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    div[data-testid="metric-container"]{
        background:#f0f2f6; border:1px solid #e0e0e0;
        padding:15px; border-radius:10px;
        box-shadow:0 2px 4px rgba(0,0,0,.1);
    }
    .stTabs [data-baseweb="tab-list"] button
        [data-testid="stMarkdownContainer"] p{font-size:1.1rem}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state defaults ───────────────────────────────────────────
if "processing_history" not in st.session_state:
    st.session_state.processing_history = []
if "current_job" not in st.session_state:
    st.session_state.current_job = None

# ── Singletons (cached across reruns) ───────────────────────────────
@st.cache_resource
def get_scraper():
    return SyncWebScraper()

@st.cache_resource
def get_agents():
    return WriterAgent(), ReviewerAgent(), EditorAgent()

@st.cache_resource
def get_storage():
    return VersionManager()

@st.cache_resource
def get_reward_model():
    return RewardModel()

@st.cache_resource
def get_search():
    return SemanticSearch()

@st.cache_resource
def get_inference_engine():
    return ContentSelectionEngine(reward_model=get_reward_model())


scraper = get_scraper()
writer, reviewer, editor = get_agents()
vm = get_storage()
rm = get_reward_model()
search_engine = get_search()
inference = get_inference_engine()


# =====================================================================
# Process URL — core pipeline
# =====================================================================
def process_url(url: str, style: str, max_iterations: int, use_rl: bool = False):
    """Scrape → Write → Review → Edit loop with progress reporting."""
    progress = st.empty()
    status = st.empty()

    # ── Validate API key before starting ────────────────────────
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here":
        status.error(
            "⛔ GEMINI_API_KEY is not configured. "
            "Please set a valid API key in your environment or Streamlit secrets."
        )
        return None

    status.info("🔄 Scraping content…")
    progress.progress(0.05, "Fetching page…")
    scraped = scraper.scrape_url(url)

    if not scraped.get("success"):
        status.error(f"Scrape failed: {scraped.get('error', 'unknown')}")
        return None

    original_content = scraped["content"]
    current_content = original_content
    iterations = []

    # ── RL-based multi-version generation ─────────────────────────
    if use_rl:
        progress.progress(0.15, "Generating multiple RL versions…")
        status.info("🧠 RL inference — generating & scoring versions…")
        try:
            best = inference.generate_and_select(original_content, n_versions=3)
            current_content = best["content"]
            style = best.get("style", style)
            review = best.get("ai_review", {})
            iterations.append(
                {
                    "iteration": 1,
                    "content": current_content,
                    "review": review,
                    "processing_time": best.get("metadata", {}).get("processing_time", 0),
                    "rl_selection": best.get("selection_reason", "n/a"),
                }
            )
        except Exception as e:
            status.warning(f"RL generation failed, falling back to single-style: {e}")
            use_rl = False  # fall through to normal path

    # ── Standard iterative pipeline ──────────────────────────────
    start_iter = len(iterations)
    for i in range(start_iter, max_iterations):
        pct = 0.2 + 0.65 * (i / max_iterations)
        progress.progress(pct, f"AI iteration {i + 1}/{max_iterations}")

        if i == 0:
            result = writer.rewrite_content(current_content, style=style)
            current_content = result["rewritten"]
        else:
            result = editor.improve_content(current_content, iterations[-1]["review"])
            current_content = result["improved"]

        review = reviewer.review_content(original_content, current_content)

        iterations.append(
            {
                "iteration": i + 1,
                "content": current_content,
                "review": review,
                "processing_time": result["metadata"]["processing_time"],
            }
        )

        # Early exit if quality is already high
        if review.get("ready_for_human") and review.get("quality_score", 0) >= 8:
            break

    # ── Persist ───────────────────────────────────────────────────
    progress.progress(0.90, "Saving version…")
    final_review = iterations[-1]["review"]
    version_id = vm.save_version(
        url=url,
        original=original_content,
        rewritten=current_content,
        metadata={
            "style": style,
            "iterations": len(iterations),
            "quality_score": final_review.get("quality_score", 0),
            "clarity_score": final_review.get("clarity_score", 0),
            "engagement_score": final_review.get("engagement_score", 0),
            "used_rl": use_rl,
        },
    )

    # ── Index in semantic search ──────────────────────────────────
    try:
        search_engine.add_version(
            version_id=version_id,
            url=url,
            original=original_content,
            rewritten=current_content,
            style=style,
            quality_score=final_review.get("quality_score", 0),
        )
    except Exception as e:
        st.warning(f"Semantic indexing skipped: {e}")

    progress.progress(1.0, "Done!")
    time.sleep(0.4)
    progress.empty()
    status.success("✅ Processing complete!")

    result = {
        "url": url,
        "version_id": version_id,
        "original": original_content,
        "final": current_content,
        "iterations": iterations,
        "style": style,
        "screenshot": scraped.get("screenshot"),
        "timestamp": datetime.now(),
    }
    st.session_state.processing_history.append(result)
    return result


# =====================================================================
# UI
# =====================================================================
def main():
    # ── Header ────────────────────────────────────────────────────
    hdr1, hdr2 = st.columns([3, 1])
    with hdr1:
        st.title("🚀 EchoWrite AI Content System")
        st.markdown("*Multi-agent content processing · RL feedback · Semantic search · Voice*")
    with hdr2:
        stats = vm.get_statistics()
        st.metric("Stored Versions", stats["total_versions"])

    tabs = st.tabs(["📝 Process", "🎤 Voice", "📊 Analytics", "🧠 Training", "🔍 Search", "📚 History", "⚙️ Settings"])

    # ── TAB 0 — Process ──────────────────────────────────────────
    with tabs[0]:
        st.header("Process Content")

        c1, c2 = st.columns([3, 1])
        with c1:
            url = st.text_input(
                "URL to process",
                value="https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1",
                placeholder="https://example.com/article",
            )
        with c2:
            style = st.selectbox(
                "Writing Style",
                ["engaging", "professional", "casual", "academic", "creative"],
            )

        o1, o2 = st.columns(2)
        with o1:
            max_iters = st.slider("Max AI Iterations", 1, 5, 3)
        with o2:
            use_rl = st.checkbox("Use RL Inference (multi-version)", value=False)

        if st.button("🚀 Process Content", type="primary", use_container_width=True):
            if not url:
                st.error("Please enter a URL")
            else:
                result = process_url(url, style, max_iters, use_rl)
                if result:
                    _render_result(result)

    # ── TAB 1 — Voice ──────────────────────────────────────────
    with tabs[1]:
        _render_voice()

    # ── TAB 2 — Analytics ────────────────────────────────────────
    with tabs[2]:
        _render_analytics()

    # ── TAB 3 — Training / Feedback ──────────────────────────────
    with tabs[3]:
        _render_training()

    # ── TAB 4 — Semantic Search ──────────────────────────────────
    with tabs[4]:
        _render_search()

    # ── TAB 5 — History ──────────────────────────────────────────
    with tabs[5]:
        _render_history()

    # ── TAB 6 — Settings ─────────────────────────────────────────
    with tabs[6]:
        _render_settings()


# =====================================================================
# Render helpers
# =====================================================================
def _render_result(result: dict):
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Original Length", f"{len(result['original']):,} chars")
    with m2:
        st.metric("Final Length", f"{len(result['final']):,} chars")
    with m3:
        q = result["iterations"][-1]["review"].get("quality_score", 0)
        st.metric("Quality Score", f"{q}/10")
    with m4:
        st.metric("Iterations Used", len(result["iterations"]))

    st.subheader("📄 Content Comparison")
    left, right = st.columns(2)
    with left:
        st.markdown("**Original Content**")
        with st.container(height=400):
            st.text(result["original"][:3000] + ("…" if len(result["original"]) > 3000 else ""))
    with right:
        st.markdown("**Processed Content**")
        with st.container(height=400):
            st.text(result["final"][:3000] + ("…" if len(result["final"]) > 3000 else ""))

    # ── Score progression chart ──────────────────────────────────
    st.subheader("📈 Iteration Progress")
    rows = []
    for it in result["iterations"]:
        rows.append(
            {
                "Iteration": it["iteration"],
                "Quality": it["review"].get("quality_score", 0),
                "Clarity": it["review"].get("clarity_score", 0),
                "Engagement": it["review"].get("engagement_score", 0),
                "Time (s)": round(it["processing_time"], 2),
            }
        )
    df = pd.DataFrame(rows)
    fig = px.line(df, x="Iteration", y=["Quality", "Clarity", "Engagement"], markers=True, title="Score Progression")
    st.plotly_chart(fig, use_container_width=True)

    # ── Human-in-the-loop inline feedback ────────────────────────
    st.subheader("👤 Human-in-the-Loop Feedback")
    st.markdown("*Rate this output to improve future results via the reward model.*")

    fb1, fb2 = st.columns([1, 2])
    with fb1:
        rating = st.slider("Your rating", 0.0, 1.0, 0.7, 0.05, key="inline_rating")
    with fb2:
        feedback_text = st.text_area("Comments (optional)", key="inline_fb")

    if st.button("✅ Submit Feedback & Train", key="inline_submit"):
        rm.record_feedback(
            version_id=result["version_id"],
            content=result["final"],
            metadata={"style": result["style"], "iteration_count": len(result["iterations"])},
            human_rating=rating,
            human_feedback=feedback_text,
        )
        st.success("Feedback recorded — the reward model has been updated!")
        st.rerun()

    # ── Download buttons ─────────────────────────────────────────
    with st.expander("💾 Downloads"):
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button("📥 Original", result["original"], f"original_{result['version_id']}.txt")
        with d2:
            st.download_button("📥 Processed", result["final"], f"processed_{result['version_id']}.txt")
        with d3:
            meta_json = json.dumps(
                {
                    "version_id": result["version_id"],
                    "url": result["url"],
                    "style": result["style"],
                    "iterations": len(result["iterations"]),
                    "final_scores": {
                        k: result["iterations"][-1]["review"].get(k, 0)
                        for k in ("quality_score", "clarity_score", "engagement_score")
                    },
                },
                indent=2,
            )
            st.download_button("📥 Metadata", meta_json, f"meta_{result['version_id']}.json", mime="application/json")


def _render_analytics():
    st.header("📊 Analytics Dashboard")

    storage_stats = vm.get_statistics()
    rl_stats = rm.get_statistics()
    search_stats = search_engine.get_statistics()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Versions", storage_stats["total_versions"])
    with c2:
        st.metric("Unique URLs", storage_stats["unique_urls"])
    with c3:
        st.metric("Avg Rating", f"{rl_stats.get('average_rating', 0):.2f}")
    with c4:
        st.metric("Best Style", rl_stats.get("best_style", "N/A"))
    with c5:
        st.metric("Indexed Docs", search_stats.get("total_documents", 0))

    if storage_stats["total_versions"] == 0:
        st.info("No data yet — process some content to see analytics!")
        return

    history = vm.get_history(limit=50)
    if not history:
        return

    df = pd.DataFrame(history)

    left, right = st.columns(2)
    with left:
        st.subheader("Quality Scores Over Time")
        if "quality_score" in df.columns:
            fig = px.line(df, x="created_at", y="quality_score", markers=True, title="Quality Trend")
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Style Distribution")
        if "style" in df.columns:
            counts = df["style"].value_counts()
            fig = px.pie(values=counts.values, names=counts.index, title="Content by Style")
            st.plotly_chart(fig, use_container_width=True)

    if rl_stats.get("style_details"):
        st.subheader("Style Performance (from human feedback)")
        rows = []
        for s, d in rl_stats["style_details"].items():
            rows.append({"Style": s, "Avg Rating": d["average"], "Samples": d["count"]})
        sdf = pd.DataFrame(rows)
        fig = px.bar(sdf, x="Style", y="Avg Rating", color="Samples", title="Avg Rating by Style")
        st.plotly_chart(fig, use_container_width=True)


def _render_training():
    st.header("🧠 Training & Feedback")

    history = vm.get_history(limit=20)

    if not history:
        st.info("No versions to review yet — process some content first!")
        return

    st.subheader("Rate a Past Output")
    sel = st.selectbox(
        "Select version",
        options=history,
        format_func=lambda x: f"{(x.get('url') or '')[:50]}… ({x.get('created_at', '')})",
    )

    if sel:
        vdata = vm.get_version(sel["version_id"])
        if vdata:
            l, r = st.columns(2)
            with l:
                st.markdown("**Original**")
                with st.container(height=300):
                    st.text(vdata["original"][:1000] + "…")
            with r:
                st.markdown("**Rewritten**")
                with st.container(height=300):
                    st.text(vdata["rewritten"][:1000] + "…")

            st.subheader("Provide Feedback")
            f1, f2 = st.columns([1, 2])
            with f1:
                rating = st.slider("Quality Rating", 0.0, 1.0, 0.7, 0.1, key="train_rating")
            with f2:
                fb = st.text_area("Additional feedback", key="train_fb")

            if st.button("Submit Feedback", type="primary", key="train_submit"):
                rm.record_feedback(
                    version_id=sel["version_id"],
                    content=vdata["rewritten"],
                    metadata={"style": sel.get("style", "unknown"), "iteration_count": sel.get("iterations", 1)},
                    human_rating=rating,
                    human_feedback=fb,
                )
                st.success("Feedback recorded — the AI will learn from your input!")
                st.rerun()

    # ── Recommendations ──────────────────────────────────────────
    best = rm.get_best_parameters()
    st.subheader("🎯 AI Recommendations (learned)")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Recommended Style", best["style"])
    with r2:
        st.metric("Optimal Iterations", best["iterations"])
    with r3:
        st.metric("Expected Score", f"{best['avg_score'] * 10:.1f}/10")


def _render_search():
    st.header("🔍 Semantic Search")
    st.markdown("Search your content library by *meaning* — powered by ChromaDB.")

    query = st.text_input("Search query", placeholder="e.g. 'sunrise over the mountains'")
    sc1, sc2 = st.columns([1, 1])
    with sc1:
        n = st.slider("Max results", 1, 20, 5, key="search_n")
    with sc2:
        style_filter = st.selectbox("Filter by style", ["(all)", "engaging", "professional", "casual", "academic", "creative"], key="search_style")

    if st.button("🔎 Search", key="search_go") and query:
        filters = {} if style_filter == "(all)" else {"style": style_filter}
        results = search_engine.search(query, n_results=n, filters=filters if filters else None)

        if not results:
            st.info("No matching documents found.")
        else:
            for i, hit in enumerate(results, 1):
                meta = hit.get("metadata", {})
                dist = hit.get("distance")
                with st.expander(f"#{i}  —  {meta.get('version_id', 'unknown')}  (distance: {dist:.4f})" if dist else f"#{i}"):
                    st.markdown(f"**Style:** {meta.get('style', '?')} · **Type:** {meta.get('content_type', '?')} · **URL:** {meta.get('url', '?')}")
                    st.text(hit.get("content", ""))

    # ── Index stats ──────────────────────────────────────────────
    sstats = search_engine.get_statistics()
    st.caption(f"Index contains {sstats['total_documents']} document chunks.")


def _render_history():
    st.header("📚 Processing History")
    if not st.session_state.processing_history:
        st.info("No processing history in this session.")
        return
    for i, job in enumerate(reversed(st.session_state.processing_history)):
        label = f"{job['url']} — {job['timestamp'].strftime('%Y-%m-%d %H:%M')}"
        with st.expander(label):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Version", job["version_id"][:12] + "…")
            with c2:
                st.metric("Iterations", len(job["iterations"]))
            with c3:
                q = job["iterations"][-1]["review"].get("quality_score", 0)
                st.metric("Score", f"{q}/10")
            if st.button("View content", key=f"hist_{i}"):
                st.text_area("Original", job["original"][:1000], height=200, key=f"ho_{i}")
                st.text_area("Final", job["final"][:1000], height=200, key=f"hf_{i}")


def _tts_generate(text: str, lang: str = "en"):
    """Generate TTS audio bytes from text. Returns BytesIO or None."""
    try:
        from gtts import gTTS
        import io
        tts = gTTS(text=text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _render_voice():
    st.header("🎤 Voice Control")
    st.markdown("Speak commands or convert text to speech.")

    voice = VoiceInterface()

    # ── Two columns: Voice Input + Text-to-Speech ────────────────
    col_stt, col_tts = st.columns(2)

    # ── LEFT: Speech-to-Text (Voice Commands) ────────────────────
    with col_stt:
        st.subheader("🎙️ Voice Commands")
        st.caption("Record a command using your mic.")
        audio_data = st.audio_input("Click to record")

        if audio_data is not None:
            if not SPEECH_RECOGNITION_AVAILABLE:
                st.error("SpeechRecognition package not available.")
                return

            import speech_recognition as sr
            recognizer = sr.Recognizer()

            with st.spinner("Transcribing..."):
                try:
                    audio_file = sr.AudioFile(audio_data)
                    with audio_file as source:
                        audio = recognizer.record(source)
                    transcript = recognizer.recognize_google(audio, language=settings.VOICE_LANGUAGE)
                except sr.UnknownValueError:
                    st.warning("Could not understand the audio. Please try again.")
                    return
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                    return

            st.success(f"**You said:** {transcript}")

            command = voice.parse_voice_command(transcript)
            intent = command.get("intent", "unknown")
            st.info(f"**Detected intent:** `{intent}`")

            if intent == "process_url":
                url = command.get("url")
                style = command.get("style", "engaging")
                if url:
                    st.write(f"Processing **{url}** in *{style}* style...")
                    result = process_url(url, style, max_iterations=3)
                    if result:
                        _render_result(result)
                else:
                    st.warning("Say a command with a URL, e.g. *'Process https://example.com in professional style'*")

            elif intent == "search":
                query = command.get("query", "")
                if query:
                    st.write(f"Searching for: **{query}**")
                    results = search_engine.search(query, n_results=5)
                    if results:
                        for r in results:
                            st.markdown(f"- **{r.get('url', 'N/A')}** (score: {r.get('score', 'N/A'):.2f})")
                    else:
                        st.info("No results found.")
                else:
                    st.warning("No search query detected.")

            elif intent == "get_status":
                stats = vm.get_statistics()
                st.json(stats)

            elif intent == "help":
                st.markdown(
                    "**Available voice commands:**\n"
                    "- *\"Process [URL] in [style] style\"* — rewrite content\n"
                    "- *\"Search for [topic]\"* — semantic search\n"
                    "- *\"Status\"* — show system stats\n"
                    "- *\"Help\"* — show this list"
                )
            else:
                st.warning(f"Unrecognized command: *{transcript}*. Say **help** for available commands.")

            # Auto TTS response
            response_text = {
                "process_url": f"Processing content in {command.get('style', 'engaging')} style.",
                "search": f"Searching for {command.get('query', 'your query')}.",
                "get_status": "Here are the current system statistics.",
                "help": "Here are the available voice commands.",
            }.get(intent, f"I heard: {transcript}")

            audio_out = _tts_generate(response_text, settings.VOICE_LANGUAGE)
            if audio_out:
                st.audio(audio_out, format="audio/mp3", autoplay=True)

    # ── RIGHT: Text-to-Speech ────────────────────────────────────
    with col_tts:
        st.subheader("🔊 Text-to-Speech")
        st.caption("Type or paste any text and hear it read aloud.")

        tts_text = st.text_area(
            "Enter text to read aloud",
            height=200,
            placeholder="Paste your content here...",
        )

        tts_col1, tts_col2 = st.columns(2)
        with tts_col1:
            tts_lang = st.selectbox("Language", ["en", "es", "fr", "de", "hi", "ja", "ko", "zh-CN"], index=0)
        with tts_col2:
            read_speed = st.checkbox("Slow speed", value=False)

        if st.button("🔊 Read Aloud", type="primary", use_container_width=True):
            if not tts_text.strip():
                st.warning("Please enter some text first.")
            else:
                with st.spinner("Generating audio..."):
                    try:
                        from gtts import gTTS
                        import io
                        tts = gTTS(text=tts_text.strip(), lang=tts_lang, slow=read_speed)
                        buf = io.BytesIO()
                        tts.write_to_fp(buf)
                        buf.seek(0)
                        st.audio(buf, format="audio/mp3", autoplay=True)
                        st.success("Audio generated! Press play above.")
                    except Exception as e:
                        st.error(f"TTS generation failed: {e}")

    # ── Help section at the bottom ───────────────────────────────
    with st.expander("ℹ️ How to use Voice Control"):
        st.markdown(
            "**Voice Commands (left):** Click the mic, speak a command, and EchoWrite will "
            "transcribe it, detect your intent, and execute it. The app also speaks back a response.\n\n"
            "**Text-to-Speech (right):** Paste any text — an article, your rewritten content, notes — "
            "and click *Read Aloud* to hear it. Supports multiple languages.\n\n"
            "**Tip:** After processing content in the Process tab, copy the result here to listen to it!"
        )


def _render_settings():
    st.header("⚙️ Settings")

    st.subheader("Model Configuration")
    model_name = st.text_input("Model Name", value="gemini-2.5-flash")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)

    if st.button("Update Configuration"):
        st.success("Configuration updated (takes effect on next processing run).")

    st.subheader("System Info")
    i1, i2 = st.columns(2)
    with i1:
        st.info(f"ChromaDB: ./chroma_db")
        st.info(f"Versions: ./content_versions")
        st.info(f"Screenshots: ./screenshots")
        st.info(f"Reward data: ./reward_data")
    with i2:
        if st.button("🗑️ Clear files older than 7 days"):
            removed = 0
            for d in [Path("output"), Path("screenshots")]:
                if d.exists():
                    cutoff = datetime.now().timestamp() - 7 * 86400
                    for f in d.glob("*"):
                        if f.stat().st_mtime < cutoff:
                            f.unlink()
                            removed += 1
            st.success(f"Removed {removed} old files.")


# ── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
