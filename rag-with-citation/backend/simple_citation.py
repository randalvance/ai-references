import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables (e.g., ANTHROPIC_API_KEY)
load_dotenv()

def get_citation_response(context_text: str, question: str) -> str:
    """
    Invokes the Anthropic model to answer a question based on provided context with citations.
    """
    # 2. Initialize the Anthropic Model
    model = ChatAnthropic(
        model="claude-opus-4-7"
    )

    # 3. Create the Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant that answers questions based ONLY on the provided context. 
        When you provide information, you MUST cite the specific PDF page it came from using the format [[page:X]] where X is the page number. 
        Example: "The Sun is a G-type star [[page:1]]."
        If the answer is not in the context, say that you do not know."""),
        ("human", "Context:\n{context}\n\nQuestion: {question}")
    ])

    # 4. Construct the Chain
    chain = prompt | model | StrOutputParser()

    return chain.invoke({"context": context_text, "question": question})

def main():
    # 1. Define the Context
    context_text = """
    Document 1: The Solar System
    The Solar System consists of the Sun and the objects that orbit it. The Sun is a G-type main-sequence star that contains roughly 99.86% of the system's known mass.

    Document 2: Mars
    Mars is the fourth planet from the Sun and the second-smallest planet in the Solar System. It is often referred to as the "Red Planet" because of the iron oxide prevalent on its surface.

    Document 3: Jupiter
    Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass more than two and a half times that of all the other planets in the Solar System combined.
    """

    # 5. Execute with a Sample Question
    question = "What planet is known as the Red Planet and what makes it that color?"
    
    print(f"Question: {question}\n")
    print("--- Response ---")
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not found in environment.")
        return

    try:
        response = get_citation_response(context_text, question)
        print(response)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
