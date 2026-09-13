import uuid

from langchain_core.messages import HumanMessage

from devops_agents.graph import graph
from devops_agents.utils import extract_text


def print_header() -> None:
    print()
    print("=" * 60)
    print("                 DevOps Multi-Agent")
    print("=" * 60)
    print()
    print("Available agents:")
    print("  • Kubernetes")
    print("  • AWS")
    print("  • Linux")
    print()
    print("Type 'exit' to quit.")
    print()


def main() -> None:
    print_header()

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        query = input("You: ").strip()

        if query.lower() == "exit":
            print()
            print("Goodbye!")
            break

        if not query:
            continue

        try:
            result = graph.invoke(
                {
                    "messages": [HumanMessage(content=query)],
                },
                config=config,
            )

            agent = result.get("selected_agent", "Agent").capitalize()
            response = extract_text(result.get("agent_response", ""))

            print()
            print("┌" + "─" * 58 + "┐")
            print(f"│ {agent + ' Agent':<56} │")
            print("└" + "─" * 58 + "┘")
            print()
            print(response)
            print()

        except Exception as exc:
            print()
            print("!" * 60)
            print("ERROR")
            print("!" * 60)
            print(exc)
            print()


if __name__ == "__main__":
    main()