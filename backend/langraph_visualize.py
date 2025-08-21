from langgraph_agent import get_concierge_agent

agent = get_concierge_agent()
graph = agent.app.get_graph()

graph.draw_png("flow.png", fontname="Arial")
