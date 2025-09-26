from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, List, Optional
from pydantic import BaseModel, Field
from langgraph.types import Send
from langchain_groq import ChatGroq
from langchain.tools import Tool
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
import operator
from dotenv import load_dotenv
import os
import requests
from datetime import datetime
import json

load_dotenv()

# Initialize LLM
llm = ChatGroq(
    model_name='openai/gpt-oss-20b',  # More reliable model-moonshotai/kimi-k2-instruct-0905
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1  # Lower temperature for more consistent outputs
)

# Enhanced Models
class ResearchQuery(BaseModel):
    query: str = Field(description="Specific search query for gathering information")
    priority: int = Field(description="Priority level (1-5, where 5 is highest)")

class Section(BaseModel):
    name: str = Field(description="Name of the section")
    description: str = Field(description="Brief description of the main topic and concepts")
    research_queries: List[ResearchQuery] = Field(description="Specific research queries needed for this section")
    section_type: str = Field(description="Type: overview, technical, practical, analysis, or conclusion")

class Sections(BaseModel):
    sections: List[Section] = Field(description="Sections of the report")

class ResearchResult(BaseModel):
    query: str
    content: str
    source: str
    relevance_score: float

# Enhanced State Management
class State(TypedDict):
    topic: str
    user_context: Optional[str]
    sections: List[Section]
    research_results: Annotated[List[ResearchResult], operator.add]
    completed_sections: Annotated[List, operator.add]
    final_report: str
    error_log: Annotated[List[str], operator.add]

class WorkerState(TypedDict):
    section: Section
    research_results: List[ResearchResult]
    completed_sections: Annotated[List, operator.add]

class ResearchState(TypedDict):
    queries: List[ResearchQuery]
    research_results: Annotated[List[ResearchResult], operator.add]

# Tools Setup
def setup_tools():
    """Initialize research tools"""
    tools = []
    
    # Web Search Tool (using SerpAPI)
    def web_search(query: str) -> str:
        """Search the web for current information using SerpAPI"""
        try:
            from langchain_community.utilities import SerpAPIWrapper
            
            serpapi_key = os.getenv("SERPAPI_KEY")
            if not serpapi_key:
                return "Error: SERPER_API_KEY not found in environment variables"
            
            search = SerpAPIWrapper(serpapi_api_key=serpapi_key)
            results = search.run(query)
            return f"Search results for '{query}':\n{results}"
            
        except ImportError:
            return "Error: SerpAPI wrapper not installed. Install with: pip install google-search-results"
        except Exception as e:
            return f"Error in web search: {str(e)}"
    
    # Wikipedia Tool
    wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    
    # News API Tool (using NewsAPI.org)
    def get_current_news(topic: str) -> str:
        """Get current news about a topic using NewsAPI.org"""
        try:
            import requests
            from datetime import datetime, timedelta
            
            newsapi_key = os.getenv("NEWSAPI_KEY")
            if not newsapi_key:
                return "Error: NEWSAPI_KEY not found in environment variables"
            
            # Calculate date range (last 7 days)
            to_date = datetime.now().strftime('%Y-%m-%d')
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # NewsAPI endpoint
            url = "https://newsapi.org/v2/everything"
            
            params = {
                'q': topic,
                'apiKey': newsapi_key,
                'from': from_date,
                'to': to_date,
                'sortBy': 'relevancy',
                'language': 'en',
                'pageSize': 5  # Limit to top 5 results
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                return f"Error: NewsAPI returned status code {response.status_code}"
            
            data = response.json()
            
            if data['status'] != 'ok':
                return f"Error: NewsAPI error - {data.get('message', 'Unknown error')}"
            
            articles = data.get('articles', [])
            
            if not articles:
                return f"No recent news found for '{topic}'"
            
            # Format results
            news_results = []
            news_results.append(f"Recent News about '{topic}' (Last 7 days):\n")
            
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'No title')
                description = article.get('description', 'No description')
                source = article.get('source', {}).get('name', 'Unknown source')
                published_at = article.get('publishedAt', '')
                url = article.get('url', '')
                
                # Format date
                if published_at:
                    try:
                        date_obj = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%B %d, %Y')
                    except:
                        formatted_date = published_at
                else:
                    formatted_date = 'Unknown date'
                
                news_results.append(f"""
{i}. **{title}**
   - Source: {source}
   - Date: {formatted_date}
   - Summary: {description}
   - URL: {url}
""")
            
            return "\n".join(news_results)
            
        except requests.exceptions.RequestException as e:
            return f"Error making request to NewsAPI: {str(e)}"
        except Exception as e:
            return f"Error fetching news: {str(e)}"
    
    tools.extend([
        Tool(name="web_search", description="Search the web for current information", func=web_search),
        Tool(name="wikipedia", description="Search Wikipedia for encyclopedic information", func=wikipedia.run),
        Tool(name="current_news", description="Get current news and trends", func=get_current_news)
    ])
    
    return tools

tools = setup_tools()

# Enhanced Planner with Structured Output
planner = llm.with_structured_output(Sections)

# Core Nodes
def enhanced_orchestrator(state: State):
    """Enhanced orchestrator with better planning and context awareness"""
    try:
        topic = state['topic']
        user_context = state.get('user_context', '')
        
        planning_prompt = f"""You are an expert research planner and strategist. 
        Create a comprehensive research plan for the topic: "{topic}"
        
        User Context: {user_context}
        
        Break this into 4-6 highly relevant sections that ensure:
        
        STRUCTURE REQUIREMENTS:
        - Start with an engaging title and overview (no **title** or **subtitle** labels)
        - Include fundamental concepts and background
        - Cover practical implementation or real-world applications
        - Address current trends and recent developments
        - Provide specific examples and case studies
        - End with future outlook or conclusions
        
        RESEARCH FOCUS:
        - Generate 2-3 specific research queries per section
        - Prioritize queries that need current/real-time information
        - Include both foundational knowledge and latest developments
        - Consider multiple perspectives and use cases
        
        SECTION TYPES:
        - overview: Introduction and fundamentals
        - technical: Deep technical details and implementation
        - practical: Real-world applications and examples  
        - analysis: Critical analysis and comparisons
        - conclusion: Summary and future outlook
        
        For technical topics, ensure coverage of:
        - Core concepts and principles
        - Implementation details with code examples
        - Best practices and common pitfalls
        - Performance considerations
        - Integration patterns
        - Troubleshooting guides
        """
        
        result = planner.invoke([
            SystemMessage(content=planning_prompt),
            HumanMessage(content=f"Topic: {topic}\nContext: {user_context}")
        ])
        
        return {'sections': result.sections}
        
    except Exception as e:
        return {'error_log': [f"Orchestrator error: {str(e)}"]}

def research_coordinator(state: State):
    """Coordinate research activities across all sections"""
    try:
        all_queries = []
        for section in state['sections']:
            all_queries.extend(section.research_queries)
        
        # Sort by priority
        all_queries.sort(key=lambda x: x.priority, reverse=True)
        
        return {'research_results': [], 'queries': all_queries}
        
    except Exception as e:
        return {'error_log': [f"Research coordinator error: {str(e)}"]}

def research_worker(state: ResearchState):
    """Perform research using available tools"""
    try:
        results = []
        
        for query_obj in state.get('queries', [])[:10]:  # Limit concurrent queries
            query = query_obj.query
            
            # Use multiple tools for comprehensive research
            research_content = []
            
            # Wikipedia search
            try:
                wiki_result = tools[1].run(query)
                research_content.append(f"Wikipedia: {wiki_result[:500]}...")
            except:
                pass
            
            # Web search
            try:
                web_result = tools[0].run(query)
                research_content.append(f"Web: {web_result[:500]}...")
            except:
                pass
            
            # News search for current topics
            if any(keyword in query.lower() for keyword in ['current', 'latest', '2024', '2025', 'recent']):
                try:
                    news_result = tools[2].run(query)
                    research_content.append(f"News: {news_result[:500]}...")
                except:
                    pass
            
            if research_content:
                combined_content = "\n\n".join(research_content)
                results.append(ResearchResult(
                    query=query,
                    content=combined_content,
                    source="multi-source",
                    relevance_score=query_obj.priority / 5.0
                ))
        
        return {'research_results': results}
        
    except Exception as e:
        return {'error_log': [f"Research worker error: {str(e)}"]}

def enhanced_section_writer(state: WorkerState):
    """Write sections with research-backed content"""
    try:
        section = state['section']
        research_results = state.get('research_results', [])
        
        # Filter relevant research for this section
        relevant_research = [r for r in research_results 
                           if any(q.query in r.query for q in section.research_queries)]
        
        research_context = "\n\n".join([
            f"Research Query: {r.query}\nFindings: {r.content[:800]}..."
            for r in relevant_research[:3]  # Top 3 most relevant
        ])
        
        writing_prompt = f"""You are a senior technical writer and domain expert.
        
        Write a comprehensive section for: "{section.name}"
        Description: {section.description}
        Section Type: {section.section_type}
        
        RESEARCH CONTEXT:
        {research_context}
        
        WRITING GUIDELINES:
        - Use the research findings to provide accurate, current information
        - Include specific examples, statistics, and real-world cases
        - Structure with clear headings (##, ###) and formatting
        - Add code blocks for technical content using ```language
        - Use bullet points and numbered lists appropriately
        - Include > blockquotes for key insights or warnings
        - Ensure content is actionable and valuable
        - Cite sources naturally within the text
        - Maintain professional yet engaging tone
        
        TECHNICAL REQUIREMENTS (if applicable):
        - Provide working code examples
        - Explain implementation steps clearly
        - Include error handling and best practices
        - Add performance considerations
        - Show integration patterns
        
        Write a detailed, well-researched section (800-1500 words) that thoroughly covers the topic.
        """
        
        result = llm.invoke([
            SystemMessage(content=writing_prompt),
            HumanMessage(content=f"Section: {section.name}\nFocus: {section.description}")
        ])
        
        return {'completed_sections': [result.content]}
        
    except Exception as e:
        return {'error_log': [f"Section writer error: {str(e)}"]}

def quality_synthesizer(state: State):
    """Synthesize and quality-check the final report"""
    try:
        completed_sections = state['completed_sections']
        topic = state['topic']
        
        # Create table of contents
        toc = "## Table of Contents\n\n"
        for i, section in enumerate(completed_sections, 1):
            # Extract first heading from each section
            lines = section.split('\n')
            heading = next((line.replace('##', '').strip() for line in lines if line.startswith('##')), f"Section {i}")
            toc += f"{i}. [{heading}](#{heading.lower().replace(' ', '-')})\n"
        
        # Add metadata and introduction
        metadata = f"""# Research Report: {topic}
        
*Generated on: {datetime.now().strftime('%B %d, %Y')}*
*Research Sources: Multi-source analysis including web search, Wikipedia, and current news*

---

{toc}

---

"""
        
        # Combine all sections
        full_content = metadata + "\n\n---\n\n".join(completed_sections)
        
        # Add conclusion if not present
        if "conclusion" not in full_content.lower():
            conclusion = f"""
---

## Conclusion

This comprehensive analysis of {topic} provides insights across multiple dimensions, from fundamental concepts to practical applications and future trends. The research combines authoritative sources with current developments to offer a complete perspective on the topic.

Key takeaways include the importance of understanding both theoretical foundations and practical implementation considerations, while staying updated with the rapidly evolving landscape in this domain.

---

*This report was generated using multi-agent research methodology with real-time information gathering and expert analysis.*
"""
            full_content += conclusion
        
        return {'final_report': full_content}
        
    except Exception as e:
        return {'error_log': [f"Synthesizer error: {str(e)}"]}

# Routing Functions
def route_to_research(state: State):
    """Route to research workers"""
    try:
        sections = state.get('sections', [])
        if not sections:
            return []
        
        # Collect all unique research queries
        all_queries = []
        for section in sections:
            all_queries.extend(section.research_queries)
        
        # Remove duplicates while preserving order
        unique_queries = []
        seen = set()
        for query in all_queries:
            if query.query not in seen:
                unique_queries.append(query)
                seen.add(query.query)
        
        return [Send("research_worker", {"queries": unique_queries[:15]})]  # Limit queries
        
    except Exception as e:
        return []

def route_to_writers(state: State):
    """Route to section writers with research results"""
    try:
        sections = state.get('sections', [])
        research_results = state.get('research_results', [])
        
        return [Send("enhanced_section_writer", {
            "section": section,
            "research_results": research_results
        }) for section in sections]
        
    except Exception as e:
        return []

# Build Enhanced Graph
def build_enhanced_workflow():
    """Build the complete workflow graph"""
    
    graph = StateGraph(State)
    
    # Add nodes
    graph.add_node("enhanced_orchestrator", enhanced_orchestrator)
    graph.add_node("research_worker", research_worker)
    graph.add_node("enhanced_section_writer", enhanced_section_writer)
    graph.add_node("quality_synthesizer", quality_synthesizer)
    
    # Define edges
    graph.add_edge(START, "enhanced_orchestrator")
    graph.add_conditional_edges("enhanced_orchestrator", route_to_research, ["research_worker"])
    graph.add_conditional_edges("research_worker", route_to_writers, ["enhanced_section_writer"])
    graph.add_edge("enhanced_section_writer", "quality_synthesizer")
    graph.add_edge("quality_synthesizer", END)
    
    return graph.compile(checkpointer=MemorySaver())

workflow = build_enhanced_workflow()
workflow

# Usage Example
def run_enhanced_agent(topic: str, context: str = ""):
    """Run the enhanced research agent"""
    
    workflow = build_enhanced_workflow()
    config = {"configurable": {"thread_id": f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}}
    
    initial_state = {
        "topic": topic,
        "user_context": context,
        "sections": [],
        "research_results": [],
        "completed_sections": [],
        "final_report": "",
        "error_log": []
    }
    
    try:
        result = workflow.invoke(initial_state, config=config)
        
        if result.get('error_log'):
            print("Errors encountered:")
            for error in result['error_log']:
                print(f"- {error}")
        
        return result['final_report']
        
    except Exception as e:
        return f"Workflow execution error: {str(e)}"

# Example usage
if __name__ == "__main__":
    # Test the enhanced agent
    topic = "Advanced RAG Techniques for Large Language Models in 2024"
    context = "Focus on practical implementation, performance optimization, and real-world use cases"
    
    report = run_enhanced_agent(topic, context)
    
    # Display result
    from IPython.display import Markdown, display
    display(Markdown(report))