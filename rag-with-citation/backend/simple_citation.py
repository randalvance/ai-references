from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

DocKind = Literal["pdf", "docx"]

_CITE_SPECS: dict[DocKind, tuple[str, str]] = {
    "pdf": ("[[page:X]]", "PDF page"),
    "docx": ("[[para:X]]", "paragraph"),
}


def get_citation_response(context_text: str, question: str, kind: DocKind = "pdf") -> str:
    token, unit = _CITE_SPECS[kind]
    model = ChatAnthropic(model="claude-opus-4-7")

    system_prompt = (
        "You are a helpful assistant that answers questions based ONLY on the provided context. "
        f"When you provide information, you MUST cite the specific {unit} it came from using "
        f"the format {token} where X is the {unit} number. "
        f'Example: "The Sun is a G-type star {token.replace("X", "1")}." '
        "If the answer is not in the context, say that you do not know."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ])

    chain = prompt | model | StrOutputParser()
    return chain.invoke({"context": context_text, "question": question})
