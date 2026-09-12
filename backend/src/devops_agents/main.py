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
                    "user_query": query,
                    "selected_agent": "",
                    "agent_response": "",
                }
            )

            agent = result["selected_agent"].capitalize()
            response = extract_text(result["agent_response"])

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