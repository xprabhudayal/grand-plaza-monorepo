from main_langgraph_agent import get_concierge_agent
from dotenv import load_dotenv

load_dotenv()

agent = get_concierge_agent()
graph = agent.app.get_graph()

# Save the graph visualization as a PNG file
# output_path = "FINAL_concierge_graph.png"
# graph.draw_png(output_path)

graph.draw_mermaid_png(output_file_path="FINAL-MERMAID-LANGRAPH.png")
