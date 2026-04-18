import streamlit as st
import os
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq

from prompt import placement_prompt
from pypdf import PdfReader

load_dotenv()

# API KEY CHECK
if not os.getenv("GROQ_API_KEY"):
    st.error("❌ GROQ_API_KEY not found")
    st.stop()

st.set_page_config(page_title="AI Placement Assistant", page_icon="🎯", layout="wide")

# ---------------- STYLE ---------------- #
st.markdown("""
<style>
.main {background-color:#0e1117; color:white;}
.stButton>button {background-color:#4CAF50;color:white;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ---------------- #
st.markdown("""
# 🎯 AI Placement Assistant  
### 🚀 Smart Interview Prep | Resume Analysis | Mock Interviews
""")

# ---------------- SESSION ---------------- #
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "interview_question" not in st.session_state:
    st.session_state.interview_question = None

if "interview_active" not in st.session_state:
    st.session_state.interview_active = False

# ---------------- SIDEBAR ---------------- #
st.sidebar.markdown("## 🎯 AI Assistant")

if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []

st.sidebar.markdown("---")

st.sidebar.markdown("### 👤 Profile")
cgpa = st.sidebar.slider("CGPA", 0.0, 10.0, 7.0)
skills = st.sidebar.text_input("Skills", "Python, SQL")
branch = st.sidebar.selectbox("Branch", ["CSE","IT","ECE","EEE","Mechanical"])

# Career Suggestions
if st.sidebar.button("🎯 Get Suggestions"):
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.1-8b-instant"
    )

    prompt = f"""
    CGPA: {cgpa}
    Skills: {skills}
    Branch: {branch}

    Suggest:
    - Suitable companies
    - Missing skills
    - Preparation roadmap
    """

    response = llm.invoke(prompt)
    st.sidebar.markdown("### 📊 Suggestions")
    st.sidebar.markdown(response.content)

# ---------------- SUGGESTIONS ---------------- #
st.markdown("### 💡 Try asking:")
st.write("- TCS interview process")
st.write("- How to prepare for Infosys")
st.write("- Ask me technical questions")

# ---------------- INPUT ---------------- #
company = st.selectbox("Select Company",
["TCS","Infosys","Wipro","Accenture","Cognizant","Capgemini"])

mode = st.radio("Mode", ["Chat Assistant","Mock Interview"])

uploaded_file = st.file_uploader("Upload Resume (optional)", type=["pdf"])

def extract_text(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() or "" for page in reader.pages])

# ---------------- LOAD DB ---------------- #
@st.cache_resource
def load_db():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return FAISS.load_local(
        "vectorstore",
        embeddings,
        allow_dangerous_deserialization=True
    )

# ---------------- SHOW CHAT ---------------- #
for chat in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(chat["question"])
    with st.chat_message("assistant"):
        st.markdown(chat["answer"])

# ---------------- CHAT MODE ---------------- #
if mode == "Chat Assistant":

    user_input = st.chat_input("Ask your question...")

    if user_input:
        user_input_clean = user_input.strip().lower()

        # GREETING
        if user_input_clean in ["hi", "hello", "hey"]:
            answer = "👋 Hello! Ask me anything about placements."

        # VERY SHORT INPUT
        elif len(user_input_clean) < 3:
            answer = "❗ Please enter a meaningful question."

        else:
            # INTENT DETECTION
            if "question" in user_input_clean:
                intent = "generate interview questions"
            elif "prepare" in user_input_clean:
                intent = "preparation tips"
            elif "process" in user_input_clean:
                intent = "interview process"
            else:
                intent = "placement guidance"

            db = load_db()
            retriever = db.as_retriever(search_kwargs={"k":3})

            query = f"{company} {intent} {user_input}"
            docs = retriever.invoke(query)

            context = "\n\n".join([doc.page_content for doc in docs])

            llm = ChatGroq(
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name="llama-3.1-8b-instant"
            )

            final_prompt = placement_prompt.format(
                context=context,
                question=query
            )

            with st.spinner("🤖 Thinking..."):
                response = llm.invoke(final_prompt)

            answer = response.content

            # SOURCES
            with st.expander("📚 Sources Used"):
                for doc in docs:
                    st.write(doc.metadata.get("source", "Unknown"))

        # SAVE CHAT
        st.session_state.chat_history.append({
            "question": user_input,
            "answer": answer
        })

        st.rerun()

# ---------------- MOCK INTERVIEW ---------------- #
if mode == "Mock Interview":

    if st.button("Start Interview"):
        llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-8b-instant"
        )

        response = llm.invoke(f"Generate a technical interview question for {company}")
        st.session_state.interview_question = response.content
        st.session_state.interview_active = True

    if st.session_state.interview_active:
        st.markdown("### 🧠 Question")
        st.write(st.session_state.interview_question)

        user_answer = st.text_area("Your Answer")

        if st.button("Submit Answer"):

            if not user_answer or len(user_answer.strip()) < 5:
                st.warning("❗ Please write a proper answer.")
                st.stop()

            llm = ChatGroq(
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name="llama-3.1-8b-instant"
            )

            eval_prompt = f"""
            Evaluate answer:

            Question: {st.session_state.interview_question}
            Answer: {user_answer}

            Give:
            - Overall Score /10
            - Clarity Score /10
            - Technical Score /10
            - Structure Score /10
            - Improvements
            """

            with st.spinner("📊 Evaluating..."):
                feedback = llm.invoke(eval_prompt)

            st.markdown("### 📊 Feedback")
            st.markdown(feedback.content)

# ---------------- FOOTER ---------------- #
st.markdown("---")
st.markdown("🚀 AI Placement Assistant | Powered by RAG & LLMs")