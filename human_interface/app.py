import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.sync_scraper import SyncWebScraper
from agents.writer import WriterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.editor_agent import EditorAgent
from storage.version_manager import VersionManager
from rl_models.reward_model import RewardModel

st.set_page_config(
    page_title="EchoWrite AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []
if 'current_job' not in st.session_state:
    st.session_state.current_job = None

scraper = SyncWebScraper()
writer = WriterAgent()
reviewer = ReviewerAgent()
editor = EditorAgent()
vm = VersionManager()
rm = RewardModel()

def process_url(url, style, max_iterations):
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    status_placeholder.info("🔄 Starting processing...")
    
    progress_placeholder.progress(0.1, "Scraping content...")
    scraped = scraper.scrape_url(url)
    
    if not scraped['success']:
        status_placeholder.error(f"Failed to scrape: {scraped.get('error')}")
        return None
    
    current_content = scraped['content']
    iterations = []
    
    for i in range(max_iterations):
        progress = 0.2 + (0.7 * i / max_iterations)
        progress_placeholder.progress(progress, f"AI Iteration {i+1}/{max_iterations}")
        
        if i == 0:
            result = writer.rewrite_content(current_content, style=style)
            current_content = result['rewritten']
        else:
            result = editor.improve_content(current_content, iterations[-1]['review'])
            current_content = result['improved']
        
        review = reviewer.review_content(scraped['content'], current_content)
        
        iterations.append({
            'iteration': i + 1,
            'content': current_content,
            'review': review,
            'processing_time': result['metadata']['processing_time']
        })
        
        if review.get('ready_for_human') and review.get('quality_score', 0) >= 8:
            break
    
    progress_placeholder.progress(0.9, "Saving results...")
    
    version_id = vm.save_version(
        url=url,
        original=scraped['content'],
        rewritten=current_content,
        metadata={
            'style': style,
            'iterations': len(iterations),
            'quality_score': iterations[-1]['review'].get('quality_score', 0)
        }
    )
    
    progress_placeholder.progress(1.0, "Complete!")
    time.sleep(0.5)
    progress_placeholder.empty()
    status_placeholder.success("✅ Processing complete!")
    
    result = {
        'url': url,
        'version_id': version_id,
        'original': scraped['content'],
        'final': current_content,
        'iterations': iterations,
        'timestamp': datetime.now()
    }
    
    st.session_state.processing_history.append(result)
    return result

def main():
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("🚀 EchoWrite AI Content System")
        st.markdown("Multi-agent content processing with reinforcement learning")
    
    with col2:
        storage_stats = vm.get_statistics()
        st.metric("Total Versions", storage_stats['total_versions'])
    
    tabs = st.tabs(["📝 Process", "📊 Analytics", "🧠 Training", "📚 History", "⚙️ Settings"])
    
    with tabs[0]:
        st.header("Process Content")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            url = st.text_input(
                "Enter URL to process",
                value="https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1",
                placeholder="https://example.com/article"
            )
        
        with col2:
            style = st.selectbox(
                "Writing Style",
                ["engaging", "professional", "casual", "academic", "creative"]
            )
        
        max_iterations = st.slider("Max AI Iterations", 1, 5, 3)
        
        if st.button("🚀 Process Content", type="primary", use_container_width=True):
            if url:
                with st.spinner("Processing..."):
                    result = process_url(url, style, max_iterations)
                    
                if result:
                    st.success("Processing complete!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Original Length", f"{len(result['original']):,} chars")
                    with col2:
                        st.metric("Final Length", f"{len(result['final']):,} chars")
                    with col3:
                        final_score = result['iterations'][-1]['review'].get('quality_score', 0)
                        st.metric("Quality Score", f"{final_score}/10")
                    with col4:
                        st.metric("Iterations Used", len(result['iterations']))
                    
                    st.subheader("📄 Content Comparison")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Original Content**")
                        with st.container(height=400):
                            st.text(result['original'][:2000] + "..." if len(result['original']) > 2000 else result['original'])
                    
                    with col2:
                        st.markdown("**Processed Content**")
                        with st.container(height=400):
                            st.text(result['final'][:2000] + "..." if len(result['final']) > 2000 else result['final'])
                    
                    st.subheader("📊 Iteration Progress")
                    
                    iteration_data = []
                    for it in result['iterations']:
                        iteration_data.append({
                            'Iteration': it['iteration'],
                            'Quality': it['review'].get('quality_score', 0),
                            'Clarity': it['review'].get('clarity_score', 0),
                            'Engagement': it['review'].get('engagement_score', 0),
                            'Time (s)': round(it['processing_time'], 2)
                        })
                    
                    df = pd.DataFrame(iteration_data)
                    
                    fig = px.line(df, x='Iteration', y=['Quality', 'Clarity', 'Engagement'],
                                 title='Score Progression', markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("💾 Save Options"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("📥 Download Original"):
                                st.download_button(
                                    "Download",
                                    result['original'],
                                    f"original_{result['version_id']}.txt",
                                    mime="text/plain"
                                )
                        
                        with col2:
                            if st.button("📥 Download Processed"):
                                st.download_button(
                                    "Download",
                                    result['final'],
                                    f"processed_{result['version_id']}.txt",
                                    mime="text/plain"
                                )
                        
                        with col3:
                            if st.button("📥 Download Metadata"):
                                metadata = {
                                    'url': result['url'],
                                    'version_id': result['version_id'],
                                    'timestamp': result['timestamp'].isoformat(),
                                    'iterations': len(result['iterations']),
                                    'scores': {
                                        'quality': result['iterations'][-1]['review'].get('quality_score', 0),
                                        'clarity': result['iterations'][-1]['review'].get('clarity_score', 0),
                                        'engagement': result['iterations'][-1]['review'].get('engagement_score', 0)
                                    }
                                }
                                st.download_button(
                                    "Download",
                                    json.dumps(metadata, indent=2),
                                    f"metadata_{result['version_id']}.json",
                                    mime="application/json"
                                )
            else:
                st.error("Please enter a URL")
    
    with tabs[1]:
        st.header("📊 Analytics Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        
        storage_stats = vm.get_statistics()
        rl_stats = rm.get_statistics()
        
        with col1:
            st.metric("Total Versions", storage_stats['total_versions'])
        with col2:
            st.metric("Unique URLs", storage_stats['unique_urls'])
        with col3:
            st.metric("Avg Rating", f"{rl_stats.get('average_rating', 0):.2f}")
        with col4:
            st.metric("Best Style", rl_stats.get('best_style', 'N/A'))
        
        if storage_stats['total_versions'] > 0:
            history = vm.get_history(limit=50)
            
            if history:
                df = pd.DataFrame(history)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Quality Scores Over Time")
                    if 'quality_score' in df.columns:
                        fig = px.line(df, x='created_at', y='quality_score', 
                                     title='Quality Trend', markers=True)
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("Style Distribution")
                    if 'style' in df.columns:
                        style_counts = df['style'].value_counts()
                        fig = px.pie(values=style_counts.values, names=style_counts.index,
                                    title='Content by Style')
                        st.plotly_chart(fig, use_container_width=True)
                
                if rl_stats.get('style_details'):
                    st.subheader("Style Performance")
                    style_data = []
                    for style, details in rl_stats['style_details'].items():
                        avg_rating = details['average'] / details['count'] if details['count'] > 0 else 0
                        style_data.append({
                            'Style': style,
                            'Average Rating': avg_rating,
                            'Sample Count': details['count']
                        })
                    
                    style_df = pd.DataFrame(style_data)
                    fig = px.bar(style_df, x='Style', y='Average Rating',
                                title='Average Rating by Style',
                                color='Sample Count')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet. Process some content to see analytics!")
    
    with tabs[2]:
        st.header("🧠 Training & Feedback")
        
        history = vm.get_history(limit=20)
        
        if history:
            st.subheader("Rate Recent Outputs")
            
            selected_version = st.selectbox(
                "Select version to review",
                options=history,
                format_func=lambda x: f"{x['url'][:50]}... ({x['created_at']})"
            )
            
            if selected_version:
                version_data = vm.get_version(selected_version['version_id'])
                
                if version_data:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Original**")
                        with st.container(height=300):
                            st.text(version_data['original'][:1000] + "...")
                    
                    with col2:
                        st.markdown("**Rewritten**")
                        with st.container(height=300):
                            st.text(version_data['rewritten'][:1000] + "...")
                    
                    st.subheader("Provide Feedback")
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        rating = st.slider("Quality Rating", 0.0, 1.0, 0.7, 0.1)
                    
                    with col2:
                        feedback = st.text_area("Additional Feedback (optional)")
                    
                    if st.button("Submit Feedback", type="primary"):
                        rm.record_feedback(
                            version_id=selected_version['version_id'],
                            content=version_data['rewritten'],
                            metadata={
                                'style': selected_version.get('style', 'unknown'),
                                'iteration_count': selected_version.get('iterations', 1)
                            },
                            human_rating=rating,
                            human_feedback=feedback
                        )
                        st.success("Feedback recorded! The AI will learn from your input.")
                        st.rerun()
        else:
            st.info("No versions to review yet. Process some content first!")
        
        best_params = rm.get_best_parameters()
        st.subheader("🎯 AI Recommendations")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Recommended Style", best_params['style'])
        with col2:
            st.metric("Optimal Iterations", best_params['iterations'])
        with col3:
            st.metric("Expected Score", f"{best_params['avg_score']*10:.1f}/10")
    
    with tabs[3]:
        st.header("📚 Processing History")
        
        if st.session_state.processing_history:
            for i, job in enumerate(reversed(st.session_state.processing_history)):
                with st.expander(f"{job['url']} - {job['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Version ID", job['version_id'][:8] + "...")
                    with col2:
                        st.metric("Iterations", len(job['iterations']))
                    with col3:
                        final_score = job['iterations'][-1]['review'].get('quality_score', 0)
                        st.metric("Final Score", f"{final_score}/10")
                    
                    if st.button(f"View Details", key=f"view_{i}"):
                        st.write("Original:", job['original'][:500] + "...")
                        st.write("Final:", job['final'][:500] + "...")
        else:
            st.info("No processing history in this session")
    
    with tabs[4]:
        st.header("⚙️ Settings")
        
        st.subheader("Model Configuration")
        
        model_name = st.text_input("Model Name", value="gemini-pro")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
        
        if st.button("Update Configuration"):
            st.success("Configuration updated!")
        
        st.subheader("System Info")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"ChromaDB Path: ./chroma_db")
            st.info(f"Output Path: ./output")
            st.info(f"Screenshots Path: ./screenshots")
        
        with col2:
            if st.button("Clear Old Files (7+ days)"):
                output_dir = Path("output")
                if output_dir.exists():
                    cutoff = datetime.now().timestamp() - (7 * 24 * 3600)
                    removed = 0
                    for file in output_dir.glob("*"):
                        if file.stat().st_mtime < cutoff:
                            file.unlink()
                            removed += 1
                    st.success(f"Removed {removed} old files")

if __name__ == "__main__":
    main()