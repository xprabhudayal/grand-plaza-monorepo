from langgraph_agent import get_concierge_agent

agent = get_concierge_agent()
graph = agent.app.get_graph()

# Save the graph visualization as a PNG file
output_path = "concierge_graph.png"
graph.draw_png(output_path)

