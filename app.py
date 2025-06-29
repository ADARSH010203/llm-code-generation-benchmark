import asyncio
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from model_service import get_parallel_responses
from code_ingestion import ingest_github_repo
from code_evaluation import evaluate_code

load_dotenv()

# Set page config
st.set_page_config(
    page_title="Code Generation Model Comparison",
    layout="wide"
)

# Custom CSS for responsive code containers
st.markdown("""
<style>
    .stMarkdown {
        width: 100%;
    }
    pre {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        max-width: 100% !important;
    }
    code {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        max-width: 100% !important;
    }
    .streamlit-expanderContent {
        width: 100% !important;
    }
    div[data-testid="stCodeBlock"] {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'context' not in st.session_state:
    st.session_state.context = None
if 'reference_code' not in st.session_state:
    st.session_state.reference_code = None
if 'last_generated_code' not in st.session_state:
    st.session_state.last_generated_code = {"aya_expanse": None, "llama_scout": None}
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = {"aya_expanse": None, "llama_scout": None}

with st.sidebar:
    st.title("Configuration")
    
    github_repo = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repository"
    )
    
    if st.button("Ingest Repository"):
        if github_repo:
            with st.spinner("Ingesting repository..."):
                st.session_state.context = ingest_github_repo(github_repo)
            st.success("Repository ingested successfully!")
        else:
            st.error("Please enter a valid repository URL")
    
    st.session_state.reference_code = st.text_area(
        "Reference Code (Optional)",
        help="Enter reference/ground truth code to compare against",
        height=200
    )

    # Evaluation section
    st.write("### Evaluation")
    if st.button("Evaluate Generated Code"):
        if st.session_state.last_generated_code["aya_expanse"] and st.session_state.last_generated_code["llama_scout"]:
            with st.spinner("Evaluating code..."):
                st.session_state.evaluation_results["aya_expanse"] = evaluate_code(
                    st.session_state.last_generated_code["aya_expanse"],
                    st.session_state.reference_code if st.session_state.reference_code else None
                )
                st.session_state.evaluation_results["llama_scout"] = evaluate_code(
                    st.session_state.last_generated_code["llama_scout"],
                    st.session_state.reference_code if st.session_state.reference_code else None
                )
            st.success("Evaluation complete!")
        else:
            st.error("Please generate code from both models first")

async def handle_chat_input(prompt: str):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get streaming responses from both models
    with st.chat_message("assistant"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("##### Cohere Aya Expanse")
            aya_container = st.empty()
            aya_container = aya_container.code("", language="python")
        with col2:
            st.write("##### Meta Llama Scout")
            llama_container = st.empty()
            llama_container = llama_container.code("", language="python")
        
        llama_gen, aya_gen = await get_parallel_responses(prompt, st.session_state.context)
        
        async def process_llama_stream(container):
            response_text = ""
            async for chunk in llama_gen:
                response_text += chunk
                cleaned_text = response_text.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
                container.code(cleaned_text, language="python")
            return cleaned_text

        async def process_aya_stream(container):
            response_text = ""
            async for chunk in aya_gen:
                response_text += chunk
                cleaned_text = response_text.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
                container.code(cleaned_text, language="python")
            return cleaned_text

        # Run both streams concurrently
        final_llama_response, final_aya_response = await asyncio.gather(
            process_llama_stream(llama_container),
            process_aya_stream(aya_container)
        )
        
        message = {
            "role": "assistant",
            "content": "",
            "llama_response": final_llama_response,
            "aya_response": final_aya_response
        }
        st.session_state.chat_history.append(message)
        st.session_state.last_generated_code["llama_scout"] = final_llama_response
        st.session_state.last_generated_code["aya_expanse"] = final_aya_response

# Main interface
st.title("Cohere Aya Expanse vs Meta Llama Scout using DeepEval")

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
    if message["role"] == "assistant":
        col1, col2 = st.columns(2)
        with col1:
            st.write("##### Cohere Aya Expanse")
            st.code(message["aya_response"], language="python")
        with col2:
            st.write("##### Meta Llama Scout")
            st.code(message["llama_response"], language="python")

if prompt := st.chat_input("What code would you like to generate?"):
    if not st.session_state.context:
        st.error("Please ingest a GitHub repository first!")
    else:
        asyncio.run(handle_chat_input(prompt))

# Display evaluation results
if st.session_state.evaluation_results["aya_expanse"] and st.session_state.evaluation_results["llama_scout"]:
    st.write("---")
    st.header("Evaluation results generated with GPT-4o using DeepEval")

    plot_data = pd.DataFrame({
        'Metric': ["Correctness", "Readability", "Best Practices", "Overall Score"],
        'Aya Expanse': [
            st.session_state.evaluation_results['aya_expanse']['detailed_metrics']['correctness']['score'],
            st.session_state.evaluation_results['aya_expanse']['detailed_metrics']['readability']['score'],
            st.session_state.evaluation_results['aya_expanse']['detailed_metrics']['best_practices']['score'],
            st.session_state.evaluation_results['aya_expanse']['overall_score']
        ],
        'Llama Scout': [
            st.session_state.evaluation_results['llama_scout']['detailed_metrics']['correctness']['score'],
            st.session_state.evaluation_results['llama_scout']['detailed_metrics']['readability']['score'],
            st.session_state.evaluation_results['llama_scout']['detailed_metrics']['best_practices']['score'],
            st.session_state.evaluation_results['llama_scout']['overall_score']
        ]
    })
    
    fig = px.bar(
        plot_data.melt('Metric', var_name='Model', value_name='Score'),
        x='Metric',
        y='Score',
        color='Model',
        barmode='group',  
        title='Model Performance Comparison',
        template='plotly_dark',  
        color_discrete_sequence=['#00CED1', '#FF69B4'] 
    )
    
    fig.update_layout(
        xaxis_title="Evaluation Metrics",
        yaxis_title="Score",
        legend_title="Models",
        plot_bgcolor='rgba(32, 32, 32, 1)',  
        paper_bgcolor='rgba(32, 32, 32, 1)',  
        bargap=0.2,  
        bargroupgap=0.1,  
        font=dict(color='#E0E0E0'),  
        title_font=dict(color='#E0E0E0'),  
        showlegend=True,
        legend=dict(
            bgcolor='rgba(32, 32, 32, 0.8)',
            bordercolor='rgba(255, 255, 255, 0.3)',
            borderwidth=1
        )
    )
    
    fig.update_xaxes(
        gridcolor='rgba(128, 128, 128, 0.2)',
        zerolinecolor='rgba(128, 128, 128, 0.2)'
    )
    fig.update_yaxes(
        gridcolor='rgba(128, 128, 128, 0.2)',
        zerolinecolor='rgba(128, 128, 128, 0.2)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.write("### Cohere Aya Expanse detailed metrics")
    
    aya_data = []
    for metric in ["correctness", "readability", "best_practices"]:
        row = {
            "Metric": metric.title(),
            "Score": f"{st.session_state.evaluation_results['aya_expanse']['detailed_metrics'][metric]['score']:.2f}",
            "Reasoning": st.session_state.evaluation_results['aya_expanse']['detailed_metrics'][metric]['reason']
        }
        aya_data.append(row)
    
    aya_data.append({
        "Metric": "Overall Score",
        "Score": f"{st.session_state.evaluation_results['aya_expanse']['overall_score']:.2f}",
        "Reasoning": "Final weighted average"
    })
    
    # Display aya table
    aya_df = pd.DataFrame(aya_data)
    st.dataframe(
        aya_df,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="small"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Reasoning": st.column_config.TextColumn("Reasoning", width="large")
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.write("### Meta Llama Scout detailed metrics")
    
    llama_data = []
    for metric in ["correctness", "readability", "best_practices"]:
        row = {
            "Metric": metric.title(),
            "Score": f"{st.session_state.evaluation_results['llama_scout']['detailed_metrics'][metric]['score']:.2f}",
            "Reasoning": st.session_state.evaluation_results['llama_scout']['detailed_metrics'][metric]['reason']
        }
        llama_data.append(row)
    
    llama_data.append({
        "Metric": "Overall Score",
        "Score": f"{st.session_state.evaluation_results['llama_scout']['overall_score']:.2f}",
        "Reasoning": "Final weighted average"
    })
    
    # Display llama table
    llama_df = pd.DataFrame(llama_data)
    st.dataframe(
        llama_df,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="small"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Reasoning": st.column_config.TextColumn("Reasoning", width="large")
        },
        hide_index=True,
        use_container_width=True
    ) 