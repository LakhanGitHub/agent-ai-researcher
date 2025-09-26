from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, List
from pydantic import BaseModel, Field
from langgraph.types import Send
from langchain_groq import ChatGroq
import operator
from dotenv import load_dotenv
import os

load_dotenv()

#os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')openai/gpt-oss-20b
llm = ChatGroq(model_name='openai/gpt-oss-20b',# moonshotai/kimi-k2-instruct-0905
               api_key=os.getenv("GROQ_API_KEY"))




class Section(BaseModel):
    name: str = Field(description='Name fo the Section of the repot')
    description:str = Field(description='Breif description fo the main topic and concetp of the section')

class Sections(BaseModel):
    sections:List[Section]=Field(description='Section of the reprot')

planner =  llm.with_structured_output(Sections)

#Graph State
class state(TypedDict):
    topic:str
    sections:list[Section]
    completed_sections:Annotated[list, operator.add]
    final_report:str

#worker state
class WorkerState(TypedDict):
    section:Section
    completed_sections:Annotated[list, operator.add]
    
#nodes
def orchestrator(state:state):
    """"orchetrator that generate a structured plan for the report"""
    
    #generate query
    report_sections = planner.invoke(
       [ SystemMessage(content="""You are a research planner. 
         Given a report topic, break it into 4-6 highly relevant sections that cover:
         - generate engaging title and subtile of the topic (do not include words **title** & **subtitle** itself)
         -Specific research for each section to ensure depth
         - explian Problem or context if required
         - Proposed solution/approach
         - Key features/capabilities if required
         - Benefits & impact if required
         - Real-world examples/use cases if required
         
        For technical topics always include below pointers :
        - Fundamentals and core concepts
        - Practical implementation details
        - use snipits for block of codes
        - Advanced techniques and best practices
        - Real-world applications and case studies
        - Common pitfalls and troubleshooting
        - Future trends and developments

         Each section should directly connect to the given topic. Avoid generic or unrelated sections."""),
        HumanMessage(content=f"""here is the report topic:{state['topic']}\n
         Consider:
        - What would a professional need to know about this topic?
        -What examples would be most valuable?
                     
                     """)
       ]
    )

    return {'sections':report_sections.sections}

#llm call
def llm_call(state:WorkerState):
    """"workds write a section of the report"""
    section = llm.invoke(
        [
            SystemMessage(content="""You are a senior technical writer and researcher with expertise across multiple domains. 
            Write a detailed, reader engaging section of a report based on the given section name and description. 
            -Core concepts and principles
            -Stay directly relevant to the overall topic. 
            -Expand with clear explanations, examples, and real-world context.
            -Use markdown formatting (## for headings,### for subheadings, bullet points for list,**bold** for emphasis,> for important notes/tips where useful).
            - Avoid generic content — always tie back to the report's topic.
            """),
            HumanMessage(content=f"here is the section name:{state['section'].name} and description: {state['section'].description}")
        ]
    )
    return {'completed_sections':[section.content]}

#create conditional edge function to create llm call
def asign_workers(stete:state):
    """asign worker to each section in the  plan"""
    #kickof write section parallel
    return [Send("llm_call", {'section':s}) for s in stete['sections']]

#create synthesizer
def synthesizer(state:state):
    """synthesize full report from section with All section content properly organized, Make it professional, well-structured,"""
    completed_section = state['completed_sections']
    completed_report_section = "\n\n--\n\n".join(completed_section)
    return {'final_report':completed_report_section}

#workflow
graph = StateGraph(state)

graph.add_node('orchestrator',orchestrator)
graph.add_node('llm_call',llm_call)
graph.add_node('synthesizer', synthesizer)


#difine edges
graph.add_edge(START,'orchestrator')
graph.add_conditional_edges('orchestrator', asign_workers,['llm_call'])
graph.add_edge('llm_call', 'synthesizer')
graph.add_edge('synthesizer', END)



workflow = graph.compile(checkpointer=MemorySaver())
workflow

config = {"configurable": {"thread_id": "thread_1"}}
state = workflow.invoke({"topic":"give me top 30 interview questions on GenAI?"},config=config)

from IPython.display import Markdown
Markdown(state['final_report'])