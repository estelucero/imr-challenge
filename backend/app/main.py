from fastapi import FastAPI
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langserve import add_routes

app = FastAPI(title="LangChain Dev Server")

model = init_chat_model(
    "openrouter:anthropic/claude-haiku-5.5:batch",
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
)

prompt = ChatPromptTemplate.from_template("Explícame qué es {tema} en dos líneas.")
chain = prompt | model

# Esto crea automáticamente endpoints (/chain/invoke, /chain/playground, etc.)
add_routes(app, chain, path="/chain")

@app.get("/health")
def health():
    return {"status": "ok"}