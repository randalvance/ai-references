from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


def get_citation_response(context_text: str, question: str) -> str:
    model = ChatAnthropic(model="claude-opus-4-7")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant that answers questions based ONLY on the provided context.
        When you provide information, you MUST cite the specific PDF page it came from using the format [[page:X]] where X is the page number.
        Example: "The Sun is a G-type star [[page:1]]."
        If the answer is not in the context, say that you do not know."""),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ])

    chain = prompt | model | StrOutputParser()
    return chain.invoke({"context": context_text, "question": question})
