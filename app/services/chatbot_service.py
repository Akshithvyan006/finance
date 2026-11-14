import re
from typing import Dict, Any, List, Optional
from app.security.guardrails import (
    detect_prompt_injection,
    sanitize_chat_input,
    EDUCATIONAL_DISCLAIMER,
)

# Knowledge Base with predefined topics, keywords, explanations, and action items
FINANCIAL_KNOWLEDGE_BASE = [
    {
        "topic": "Savings & Emergency Funds",
        "keywords": ["saving", "savings", "emergency fund", "high yield", "hysa", "rainy day", "liquid cash"],
        "summary": "Building a resilient emergency reserve and maximizing yield on liquid cash.",
        "content": (
            "An emergency fund is your primary financial shock absorber. "
            "Financial guidelines recommend holding 3 to 6 months of essential living expenses (housing, utilities, food, insurance) "
            "in an easily accessible, FDIC/NCUA-insured High-Yield Savings Account (HYSA).\n\n"
            "Key strategies:\n"
            "1. Pay Yourself First: Automate transfers on payday before discretionary spending occurs.\n"
            "2. Keep it Separate: Store emergency cash in a dedicated bank account away from your daily checking account.\n"
            "3. Tiered Reserves: Keep 1 month in checking/standard savings and 3-5 months in an HYSA earning competitive yields."
        ),
        "calculation_tip": "Try our Savings & Compound Interest Calculator to project how monthly automated deposits grow over 3 to 10 years."
    },
    {
        "topic": "Budgeting Methods (50/30/20 & Zero-Based)",
        "keywords": ["budget", "budgeting", "50/30/20", "zero based", "envelope", "track spending", "allocate income"],
        "summary": "Structuring your net take-home income into clear, sustainable categories.",
        "content": (
            "Budgeting gives every dollar a defined purpose. The most widely adopted framework is the 50/30/20 rule:\n"
            "• 50% Needs: Non-negotiable costs (housing, groceries, utilities, minimum debt payments, healthcare).\n"
            "• 30% Wants: Discretionary lifestyle choices (dining out, entertainment, subscriptions, hobbies).\n"
            "• 20% Financial Goals: Emergency fund funding, extra debt paydown, and retirement/investment accounts.\n\n"
            "Alternative: 'Zero-Based Budgeting' where Income - (Expenses + Savings) = $0, ensuring no idle unallocated money."
        ),
        "calculation_tip": "Use our Budget Calculator tab to enter your exact monthly net income and generate your customized allocation."
    },
    {
        "topic": "Expense Optimization & Tracking",
        "keywords": ["expense", "expenses", "spending", "cut costs", "reduce bill", "subscription", "lifestyle creep"],
        "summary": "Identifying spending leaks, auditing recurring subscriptions, and curbing lifestyle inflation.",
        "content": (
            "Expense optimization focuses on value-based spending without sacrificing quality of life:\n"
            "1. Audit Subscriptions: Review bank statements for zombie streaming, gym, or software subscriptions billed monthly or annually.\n"
            "2. Negotiate Fixed Bills: Inquire about retention rates or shop competitors for auto insurance, home internet, and mobile carriers.\n"
            "3. The 48-Hour Rule: For non-essential purchases over $50, enforce a 48-hour cooling-off period to prevent impulse buying."
        ),
        "calculation_tip": "Reallocating just $100/month saved from trimmed expenses into a 7% index fund yields over $17,000 in 10 years."
    },
    {
        "topic": "Debt Repayment Strategies (Snowball vs. Avalanche)",
        "keywords": ["loan", "loans", "debt", "repay", "snowball", "avalanche", "apr", "interest rate", "credit card debt"],
        "summary": "Structured frameworks for accelerating debt elimination.",
        "content": (
            "When dealing with non-mortgage debt, two proven methodologies exist:\n\n"
            "1. Debt Avalanche (Mathematically Optimal):\n"
            "Pay minimums on all obligations, then channel all surplus funds into the loan with the highest interest rate (APR). "
            "This minimizes total interest paid across your lifetime.\n\n"
            "2. Debt Snowball (Psychologically Motivating):\n"
            "Pay minimums on all obligations, then attack the loan with the smallest dollar balance first. "
            "Eliminating balances quickly creates behavioral momentum and reduces cognitive burden."
        ),
        "calculation_tip": "Input your loan balance, term, and interest rate in our Loan Amortization Calculator to see your exact monthly interest breakdown."
    },
    {
        "topic": "Inflation & Purchasing Power Erosion",
        "keywords": ["inflation", "purchasing power", "cpi", "cost of living", "real return", "nominal return", "erosion"],
        "summary": "Understanding how currency devaluation affects cash reserves and long-term wealth.",
        "content": (
            "Inflation represents the general increase in prices and fall in the purchasing value of money over time:\n"
            "• The Rule of 72: Divide 72 by the annual inflation rate to find how many years it takes for your money's purchasing power to cut in half (at 3% inflation, ~24 years).\n"
            "• Cash Drag: Keeping excessive cash beyond your emergency fund in a checking account at 0.05% interest guarantees a negative real return.\n"
            "• Historical Hedges: Broad-market equities, real assets, and Treasury Inflation-Protected Securities (TIPS) have historically outpaced inflation over multi-decade cycles."
        ),
        "calculation_tip": "Analyst role users can explore the Macro Indicators tab to inspect historical inflation vs. benchmark interest rate curves."
    },
    {
        "topic": "Investment Education & Wealth Accumulation",
        "keywords": ["invest", "investing", "investment", "stocks", "bonds", "etf", "index fund", "diversification", "compound", "401k", "ira", "portfolio"],
        "summary": "Core principles of asset allocation, index investing, and compound growth.",
        "content": (
            "Long-term investing harnesses the compounding power of productive enterprise:\n"
            "1. Asset Allocation: The distribution of your assets across equities (growth engines) and fixed income (volatility dampeners) based on your time horizon.\n"
            "2. Broad Diversification: Low-cost total stock market or S&P 500 index funds avoid the idiosyncratic risk of individual company bankruptcy.\n"
            "3. Tax-Advantaged Accounts: Maximize employer 401(k) matches first (guaranteed 100% instant return), followed by Roth IRA or HSA options."
        ),
        "calculation_tip": "Check the Savings & Compound Calculator with an estimated 7% return over 20-30 years to visualize compound interest exponential curves."
    }
]

SUGGESTED_PROMPTS = [
    "How does the 50/30/20 budgeting rule work?",
    "What is the difference between the Debt Snowball and Debt Avalanche methods?",
    "How much should I keep in an emergency savings fund?",
    "How does inflation erode cash savings over time?",
    "What are index funds and why is diversification important?",
    "How can I audit and optimize my monthly expenses?"
]


def process_chat_query(raw_prompt: str) -> Dict[str, Any]:
    """Process user query with security checks, keyword intent matching, and fallback responses."""
    # Step 1: Sanitize input length and control characters
    prompt = sanitize_chat_input(raw_prompt)

    if not prompt or len(prompt) < 2:
        return {
            "success": False,
            "error": "Query cannot be empty. Please enter a financial question.",
            "is_security_violation": False,
            "suggested_prompts": SUGGESTED_PROMPTS[:3]
        }

    # Step 2: Guardrails - Prompt Injection & Sensitive Data Leakage Detection
    is_injection, violation_reason = detect_prompt_injection(prompt)
    if is_injection:
        return {
            "success": False,
            "error": "Security Alert: Input violated security policy. Malicious instructions or unauthorized system inquiries are strictly rejected.",
            "is_security_violation": True,
            "violation_reason": violation_reason,
            "topic": "Security Policy Enforcement",
            "reply": "I am a secure financial analysis chatbot designed strictly for financial education (budgeting, savings, loans, inflation, and investing). Prompt injection, jailbreak attempts, or requests for system internals are prohibited and audited.",
            "disclaimer": EDUCATIONAL_DISCLAIMER,
        }

    # Step 3: Match against financial domain knowledge base
    prompt_lower = prompt.lower()
    matched_topics: List[Dict[str, Any]] = []

    for item in FINANCIAL_KNOWLEDGE_BASE:
        score = 0
        for kw in item["keywords"]:
            # Exact word boundary or substring match
            if re.search(r"\b" + re.escape(kw) + r"\b", prompt_lower):
                score += 3
            elif kw in prompt_lower:
                score += 1
        if score > 0:
            matched_topics.append({"item": item, "score": score})

    # Sort matches by score descending
    matched_topics.sort(key=lambda x: x["score"], reverse=True)

    if matched_topics:
        best_match = matched_topics[0]["item"]
        return {
            "success": True,
            "topic": best_match["topic"],
            "summary": best_match["summary"],
            "reply": best_match["content"],
            "calculation_tip": best_match["calculation_tip"],
            "related_topics": [m["item"]["topic"] for m in matched_topics[1:3]],
            "disclaimer": EDUCATIONAL_DISCLAIMER,
        }

    # Step 4: Graceful fallback for unsupported or out-of-domain questions
    return {
        "success": True,
        "is_fallback": True,
        "topic": "General Financial Inquiry",
        "reply": (
            "I could not locate an exact match for your question within my current financial analysis knowledge base.\n\n"
            "I specialize in the following financial topics:\n"
            "• Savings & Emergency Funds (high-yield savings, automated deposits)\n"
            "• Budgeting Frameworks (50/30/20 rule, zero-based allocation)\n"
            "• Expense Tracking & Optimization\n"
            "• Debt & Loan Repayment (Snowball vs Avalanche)\n"
            "• Inflation & Purchasing Power Impact\n"
            "• Basic Investing Concepts (Index funds, diversification, compound interest)\n\n"
            "Please try rephrasing your question or select one of the suggested prompts below."
        ),
        "suggested_prompts": SUGGESTED_PROMPTS,
        "disclaimer": EDUCATIONAL_DISCLAIMER,
    }
