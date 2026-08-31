"""
Golden Benchmark Dataset for RAG & Agent Evaluation.
Contains verified test queries, ground truth references, and domain categories
extracted directly from internal company policies.
"""

GOLDEN_RAG_DATASET = [
    {
        "query": "What are the rules for cancelling an order and when is it prohibited?",
        "ground_truth": "An order can only be cancelled if its displayStatus is 'Order Processing'. Once the status changes to 'In Escrow' or 'Closed', cancellations are strictly prohibited.",
        "category": "Order Cancellations"
    },
    {
        "query": "How long do refunds take for wire transfers, and what is the escalation keyword?",
        "ground_truth": "Wire Transfer refunds may take up to 14 business days. If delayed beyond 15 days, a ticket must be raised with billing using the keyword 'ESCALATE-REFUND'.",
        "category": "Refund Policies"
    },
    {
        "query": "What should an employee do if their laptop hardware breaks down?",
        "ground_truth": "For hardware failures like laptop breakdown, employees must raise a Level 2 ticket on the internal ServiceNow portal under the 'Hardware-Replace' category.",
        "category": "IT Support"
    },
    {
        "query": "What are the lunch timings and where are free snacks available?",
        "ground_truth": "Hot meals are served exclusively between 12:30 PM and 2:30 PM. Free coffee, tea, and dry snacks are available on the 3rd floor cafeteria all day.",
        "category": "Cafeteria Operations"
    },
    {
        "query": "Can I get a refund on gym membership through the company portal?",
        "ground_truth": "The company policies do not mention any gym membership refund rules.",
        "category": "Out-of-Scope / Hallucination Test"
    }
]