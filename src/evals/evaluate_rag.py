"""
RAG Evaluation & EvalOps Pipeline.
Implements LLM-as-a-Judge benchmark scoring across Faithfulness,
Answer Relevance, and Retrieval Accuracy with rate-limiting protection.
"""

import os
import sys

# Ensure project root directory is always in Python's search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import asyncio
import logging
from dotenv import load_dotenv
import google.generativeai as genai

# Import local services and golden dataset
from src.services.rag_service import query_knowledge_base
from src.evals.golden_dataset import GOLDEN_RAG_DATASET

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger("rag_evaluator")

# Using the active gemini-2.5-flash model
judge_model = genai.GenerativeModel("models/gemini-2.5-flash")

async def evaluate_single_sample(sample: dict) -> dict:
    """
    Executes a single RAG pipeline run, retrieves contexts, generates an answer,
    and invokes the Judge LLM with retry tolerance.
    """
    query = sample["query"]
    ground_truth = sample["ground_truth"]
    category = sample["category"]

    # 1. Retrieval Phase: Fetch context chunks from ChromaDB
    retrieved_context = query_knowledge_base(query)

    # 2. Generation Phase: Generate an answer using the retrieved context
    generation_prompt = f"""
    You are an enterprise assistant. Answer the user query strictly using the provided context.
    If the context does not contain the answer, state clearly that no relevant information is available.
    
    Context:
    {retrieved_context}
    
    User Query: {query}
    """
    
    # Retry mechanism for generation phase
    gen_response = None
    for attempt in range(3):
        try:
            gen_response = await judge_model.generate_content_async(generation_prompt)
            break
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"   ⏳ [Rate Limit] Generation paused for 15s (Attempt {attempt+1}/3)...")
                await asyncio.sleep(15)
            else:
                logger.error(f"Generation error: {e}")
                break

    generated_answer = gen_response.text.strip() if gen_response else "Failed to generate answer."

    # 3. Evaluation Phase: LLM-as-a-Judge scoring rubric
    eval_rubric_prompt = f"""
    You are an expert AI Evaluation Judge. Evaluate the following RAG output based on three metrics.
    Return ONLY a valid JSON object with scores between 0.0 and 1.0 and a brief reason.

    INPUT DATA:
    - User Query: {query}
    - Ground Truth Reference: {ground_truth}
    - Retrieved Context: {retrieved_context}
    - Generated Answer: {generated_answer}

    SCORING METRICS (0.0 to 1.0):
    1. faithfulness: Is every claim in the generated answer directly supported by the retrieved context? (1.0 = zero hallucination, 0.0 = completely fabricated).
    2. answer_relevance: Does the generated answer directly and concisely address the user query without irrelevant fluff? (1.0 = perfectly relevant).
    3. retrieval_precision: Did the retrieved context contain the essential facts necessary to match the ground truth? (1.0 = perfect retrieval).

    RESPONSE FORMAT (Strict JSON only, no markdown formatting):
    {{
        "faithfulness": 1.0,
        "answer_relevance": 1.0,
        "retrieval_precision": 1.0,
        "critique": "Short one-sentence explanation"
    }}
    """

    scores = {}
    for attempt in range(3):
        try:
            eval_response = await judge_model.generate_content_async(eval_rubric_prompt)
            clean_json_str = eval_response.text.replace("```json", "").replace("```", "").strip()
            scores = json.loads(clean_json_str)
            break
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"   ⏳ [Rate Limit] Judge evaluation paused for 15s (Attempt {attempt+1}/3)...")
                await asyncio.sleep(15)
            else:
                scores = {
                    "faithfulness": 0.0,
                    "answer_relevance": 0.0,
                    "retrieval_precision": 0.0,
                    "critique": f"Evaluation error: {str(e)}"
                }
                break

    return {
        "category": category,
        "query": query,
        "generated_answer": generated_answer,
        "faithfulness": scores.get("faithfulness", 0.0),
        "answer_relevance": scores.get("answer_relevance", 0.0),
        "retrieval_precision": scores.get("retrieval_precision", 0.0),
        "critique": scores.get("critique", "N/A")
    }

async def run_evaluation_suite():
    """
    Runs the benchmark sequentially with rate-limit pacing to respect API quotas,
    computes macro averages, and displays an executive scorecard.
    """
    print("\n" + "="*80)
    print("🚀 STARTING ENTERPRISE RAG BENCHMARK & EVALUATION SUITE")
    print("="*80 + "\n")

    results = []
    
    # Process test cases sequentially with rate pacing
    for idx, sample in enumerate(GOLDEN_RAG_DATASET, start=1):
        print(f"⏳ Evaluating Sample [{idx}/{len(GOLDEN_RAG_DATASET)}] -> {sample['category']}...")
        result = await evaluate_single_sample(sample)
        results.append(result)
        
        # Pacing pause to prevent 429 quota bursts on free tier (5 RPM)
        await asyncio.sleep(12)

    # Calculate Macro Averages
    total_faithfulness = sum(r["faithfulness"] for r in results) / len(results)
    total_relevance = sum(r["answer_relevance"] for r in results) / len(results)
    total_precision = sum(r["retrieval_precision"] for r in results) / len(results)

    print("\n" + "="*80)
    print("📋 DETAILED PER-QUERY EVALUATION BREAKDOWN")
    print("="*80)

    # Print Detailed Per-Query Results
    for idx, r in enumerate(results, start=1):
        print(f"[{idx}] Category: {r['category']}")
        print(f"    Query: {r['query']}")
        print(f"    Answer: {r['generated_answer'][:120]}...")
        print(f"    📊 Scores -> Faithfulness: {r['faithfulness']} | Relevance: {r['answer_relevance']} | Context Precision: {r['retrieval_precision']}")
        print(f"    📝 Judge Critique: {r['critique']}")
        print("-" * 80)

    # Print Final Executive Scorecard
    print("\n" + "="*80)
    print("🏆 FINAL EVALUATION EXECUTIVE SCORECARD")
    print("="*80)
    print(f"🛡️  Macro Faithfulness (Zero Hallucination) : {total_faithfulness * 100:.1f}%")
    print(f"🎯 Macro Answer Relevance (User Intent Fit) : {total_relevance * 100:.1f}%")
    print(f"📚 Macro Retrieval Precision (Context Quality): {total_precision * 100:.1f}%")
    
    overall_score = (total_faithfulness + total_relevance + total_precision) / 3 * 100
    print(f"\n⭐ Overall RAG System Quality Index: {overall_score:.1f}/100")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(run_evaluation_suite())