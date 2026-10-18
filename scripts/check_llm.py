
from app.integrations.llm import generate_answer


def main() -> None:
    answer = generate_answer(
        "In one sentence, explain what RAG is."
    )

    print("Gemini response:")
    print(answer)

    assert answer.strip(), "Gemini returned an empty answer."
    print("\nGemini API works!")


if __name__ == "__main__":
    main()
