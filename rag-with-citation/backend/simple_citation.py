from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


def get_citation_response(context_text: str, question: str) -> str:
    model = ChatAnthropic(model="claude-opus-4-7")

    system_prompt = (
        "You are a helpful assistant that answers questions based ONLY on the provided context. "
        "Each chunk in the context is labeled with its paragraph number and page (e.g. "
        "'Document (Paragraph 4, Page 2)'). Cite the specific paragraph(s) that support "
        "each statement using the format [[para:N]] where N is the paragraph number. "
        "You may additionally cite a page with [[page:P]] when paragraph granularity is not "
        "available, but prefer paragraph citations. "
        'Example: "The Sun is a G-type star [[para:3]]." '
        "If the answer is not in the context, say that you do not know."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ])

    chain = prompt | model | StrOutputParser()
    return chain.invoke({"context": context_text, "question": question})
