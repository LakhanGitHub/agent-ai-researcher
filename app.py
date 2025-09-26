import streamlit as st
import time
import re
from datetime import datetime
import os
from io import BytesIO
import base64
from agent import run_enhanced_agent


# Import your research agent (assuming it's in a separate file)
# from your_research_agent import run_enhanced_agent

# Mock function - replace with your actual import
#def run_enhanced_agent(topic: str, context: str = ""):
 #   """Mock function - replace with your actual agent"""
  #  time.sleep(2)  # Simulate processing time
   # return f"""# Research Report: {topic}

#*Generated on: {datetime.now().strftime('%B %d, %Y')}*

st.set_page_config(
    page_title="🤖 AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: .5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        color: white;
        box-shadow: 0 .5px 2px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        font-size: 3rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
    
    .research-form {
        background: white;
        padding: 2rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .sidebar-info {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .success-message {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .progress-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'research_history' not in st.session_state:
    st.session_state.research_history = []
if 'current_report' not in st.session_state:
    st.session_state.current_report = None
if 'research_count' not in st.session_state:
    st.session_state.research_count = 0

def create_download_link(content, filename):
    """Create a download link for the report"""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:text/markdown,{b64}" download="{filename}" style="text-decoration: none; color: #667eea; font-weight: 600;">📄 Download Report as Markdown</a>'

def main():
    # Main Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI Research Assistant</h1>
        <p>Powered by Multi-Agent Intelligence | Real-time Web Research | Professional Reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("Createdwith❤️byLakhan")
        st.markdown("### 💡Quick Examples")
        
        # Research Statistics
        st.markdown(f"""
        <div class="stat-card">
            <p>Topic: Latest developments in Large Language Models</p>
            <p>Context: Focus on GPT-4, Claude architectures</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="sidebar-info">
            <h4>🌟 Features</h4>
            <ul>
                <li>🌐 Real-time web search</li>
                <li>📰 Current news integration</li>
                <li>📚 Wikipedia research</li>
                <li>🤖 Multi-agent intelligence</li>
                <li>📊 Professional formatting</li>
                <li>💾 Download reports</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        
        
        # Research History
        if st.session_state.research_history:
            st.markdown("### 📈 Recent Research")
            for i, item in enumerate(st.session_state.research_history[-5:]):
                with st.expander(f"🔍 {item['topic'][:30]}..."):
                    st.write(f"**Generated:** {item['timestamp']}")
                    st.write(f"**Context:** {item['context'][:100]}...")
                    if st.button(f"View Report", key=f"history_{i}"):
                        st.session_state.current_report = item['report']
                        st.rerun()
        
        # Clear History
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.research_history = []
            st.session_state.research_count = 0
            st.success("History cleared!")
            st.rerun()
    
    # Main Content Area
    col1, = st.columns(1)
    
    with col1:
        # Research Form
        
        # Form inputs
        research_topic = st.text_input(
            "🎯 Research Topic",
            value=st.session_state.get('example_topic', ''),
            placeholder="e.g., Latest developments in quantum computing",
            help="Be specific for better results. Include key terms and focus areas."
        )
        
        research_context = st.text_area(
            "📝 Additional Context (Optional)",
            value=st.session_state.get('example_context', ''),
            placeholder="e.g., Focus on practical applications, include recent breakthroughs, compare with classical computing...",
            help="Provide additional context to guide the research focus and depth.",
            height=100
        )
        
        # Advanced Options
        with st.expander("⚙️ Advanced Options"):
            col_a, col_b = st.columns(2)
            with col_a:
                include_news = st.checkbox("📰 Include Recent News", value=True)
                include_technical = st.checkbox("🔧 Technical Details", value=True)
            with col_b:
                include_examples = st.checkbox("💼 Real-world Examples", value=True)
                include_trends = st.checkbox("📈 Future Trends", value=True)
            
            research_depth = st.select_slider(
                "📊 Research Depth",
                options=["Basic", "Standard", "Comprehensive", "Expert"],
                value="Standard"
            )
        
        # Generate Report Button
        generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
        with generate_col2:
            if st.button("🚀 Generate Research Report", type="primary", use_container_width=True):
                if research_topic.strip():
                    # Build context based on options
                    context_parts = []
                    if research_context:
                        context_parts.append(research_context)
                    if include_news:
                        context_parts.append("Include latest news and current events")
                    if include_technical:
                        context_parts.append("Provide technical details and implementation")
                    if include_examples:
                        context_parts.append("Include real-world examples and case studies")
                    if include_trends:
                        context_parts.append("Analyze future trends and predictions")
                    
                    final_context = ". ".join(context_parts)
                    
                    # Clear example values
                    if 'example_topic' in st.session_state:
                        del st.session_state.example_topic
                    if 'example_context' in st.session_state:
                        del st.session_state.example_context
                    
                    # Progress indicator
                    st.markdown("""
                    <div class="progress-container">
                        <h3>🔄 Generating Research Report...</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Simulate progress with status updates
                    stages = [
                        (20, "📋 Planning research structure..."),
                        (40, "🌐 Gathering web information..."),
                        (60, "📰 Collecting recent news..."),
                        (80, "✍️ Writing detailed sections..."),
                        (100, "📄 Finalizing report...")
                    ]
                    
                    for progress, status in stages:
                        progress_bar.progress(progress)
                        status_text.text(status)
                        time.sleep(0.5)
                    
                    try:
                        # Generate the report
                        with st.spinner("🤖 AI agents are researching..."):
                            report = run_enhanced_agent(research_topic, final_context)
                        
                        st.session_state.current_report = report
                        #st.session_state.research_count += 1
                        
                        # Add to history
                        st.session_state.research_history.append({
                            'topic': research_topic,
                            'context': final_context,
                            'report': report,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
                        })
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Research completed successfully!")
                        
                        st.markdown("""
                        <div class="success-message">
                            <strong>🎉 Research Report Generated Successfully!</strong><br>
                            Your comprehensive research report is ready. Scroll down to view the results.
                        </div>
                        """, unsafe_allow_html=True)
                        
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error generating report: {str(e)}")
                        st.info("💡 Please check your API keys and try again.")
                else:
                    st.warning("⚠️ Please enter a research topic to continue.")
    
    # Display Current Report
    if st.session_state.current_report:
        st.markdown("---")
        st.markdown("## 📄 Research Report")
        
        # Report actions
        report_col1, report_col3 = st.columns([2, 1])
        
        with report_col1:
            # Download button
            #filename = f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            st.download_button(
            label="⬇️ Download Report as Markdown",
            data=st.session_state.current_report,
            file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
            )
            #st.markdown(
                
                #create_download_link(st.session_state.current_report, filename),
                #unsafe_allow_html=True
            #)
        
        # Display the report
        st.markdown(st.session_state.current_report)
        
        
# Footer
def show_footer():
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem; color: #666;">
        <p>🤖 <strong>AI Research Assistant</strong> | Powered by Multi-Agent Intelligence</p>
        <p>Built with ❤️ by Lakhan, LangGraph, and advanced AI models</p>
        <p><small>© 2025 AI Research Assistant. All rights reserved.</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    show_footer()