from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based ONLY on the provided context. "
    "Each chunk is labeled with its paragraph number (e.g. 'Document (Paragraph 4)'). "
    "Cite the specific paragraph(s) that support each statement using the format "
    "[[para:N]] where N is the paragraph number. "
    'Example: "The Sun is a G-type star [[para:3]]." '
    "If the answer is not in the context, say that you do not know."
)

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])

_chain = None


def _get_chain():
    # Lazy so the API key (loaded by the FastAPI entry point) is available
    # by the time the model client is constructed.
    global _chain
    if _chain is None:
        _chain = _prompt | ChatAnthropic(model="claude-opus-4-7") | StrOutputParser()
    return _chain


def get_citation_response(context_text: str, question: str) -> str:
    return _get_chain().invoke({"context": context_text, "question": question})
