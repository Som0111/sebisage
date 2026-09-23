"""Drafts the Phase 3.1 evaluation question set into data/eval/questions_draft.jsonl.

Every question below was written by hand after reading the actual chunk text
cited as its `chunk_id` in data/processed/chunks_structured.jsonl (grep the id
to see the source). No LLM call is used here, so there is nothing to fabricate
or cache: these are human-authored (Claude Code, reading real regulation
text), not model-generated.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.config import EVAL_DIR

# 45 answerable questions in the regulation's own wording.
ANSWERABLE = [
    # --- LODR (13) ---
    ("What is the definition of a 'material subsidiary' under the LODR Regulations?",
     "lodr_2015", "24", "1", "definition", "easy", "lodr_2015.pdf:24:1:0"),
    ("Who must a listed entity appoint as its compliance officer?",
     "lodr_2015", "6", "1", "obligation", "easy", "lodr_2015.pdf:6:1:0"),
    ("Within how many days must a listed entity redress an investor grievance?",
     "lodr_2015", "13", "1-2", "deadline", "easy", "lodr_2015.pdf:13:1-2:0"),
    (("What minimum board composition requirements apply to a listed entity regarding "
     "women directors and non-executive directors?"),
     "lodr_2015", "17", "1", "obligation", "medium", "lodr_2015.pdf:17:1:1"),
    (("How often must the board of directors of a listed entity meet, and what is the "
     "maximum gap allowed between two meetings?"),
     "lodr_2015", "17", "2", "deadline", "easy", "lodr_2015.pdf:17:2:0"),
    (("What is the minimum size and independence requirement for the audit committee of "
     "a listed entity?"),
     "lodr_2015", "18", "1", "obligation", "medium", "lodr_2015.pdf:18:1:0"),
    (("How much advance notice must a listed entity give the stock exchange before a "
     "board meeting considering financial results?"),
     "lodr_2015", "29", "1-2", "deadline", "medium", "lodr_2015.pdf:29:1-2:0"),
    (("When must a listed entity submit its shareholding pattern statement to the stock "
     "exchange?"),
     "lodr_2015", "31", "1", "deadline", "medium", "lodr_2015.pdf:31:1:0"),
    (("What actions can a stock exchange take against a listed entity that contravenes "
     "the LODR Regulations?"),
     "lodr_2015", "98", "1", "penalty", "medium", "lodr_2015.pdf:98:1:0"),
    (("What happens if a listed entity fails to pay a fine imposed on it by the stock "
     "exchange?"),
     "lodr_2015", "99", None, "penalty", "hard", "lodr_2015.pdf:99:None:0"),
    ("On what basis must a listed entity declare and disclose dividends?",
     "lodr_2015", "43", "1", "obligation", "easy", "lodr_2015.pdf:43:1:0"),
    (("Which events require a listed entity to intimate a record date to the stock "
     "exchange?"),
     "lodr_2015", "42", "1", "obligation", "medium", "lodr_2015.pdf:42:1:0"),
    (("When must a listed company disclose a material event or information to the stock "
     "exchange?"),
     "lodr_2015", "30", "1-2", "deadline", "easy", "lodr_2015.pdf:30:1-2:0"),
    (("What board composition applies to a listed entity that has outstanding superior "
     "rights (SR) equity shares?"),
     "lodr_2015", "17", "1", "obligation", "hard", "lodr_2015.pdf:17:1:5"),
    # --- PIT (11) ---
    ("What is a 'connected person' under the PIT Regulations?",
     "pit_2015", "2", "1", "definition", "medium", "pit_2015.pdf:2:1:4"),
    ("How do the PIT Regulations define an 'insider'?",
     "pit_2015", "2", "1", "definition", "easy", "pit_2015.pdf:2:1:10"),
    ("What is 'unpublished price sensitive information' under the PIT Regulations?",
     "pit_2015", "2", "1", "definition", "easy", "pit_2015.pdf:2:1:28"),
    (("Can an insider communicate unpublished price sensitive information to another "
     "person?"),
     "pit_2015", "3", "1", "obligation", "easy", "pit_2015.pdf:3:1:0"),
    (("Within how many days must a newly appointed key managerial personnel disclose "
     "their securities holdings?"),
     "pit_2015", "7", "1", "deadline", "easy", "pit_2015.pdf:7:1:0"),
    (("Who is responsible for formulating the code of conduct to regulate trading by "
     "designated persons?"),
     "pit_2015", "9", "1", "obligation", "medium", "pit_2015.pdf:9:1:0"),
    (("What must a listed company do if it observes a violation of the code of conduct "
     "formulated under regulation 9?"),
     "pit_2015", "13", None, "obligation", "medium", "pit_2015.pdf:13:None:0"),
    (("Is an insider generally allowed to trade in securities while in possession of "
     "unpublished price sensitive information?"),
     "pit_2015", "4", "1", "obligation", "easy", "pit_2015.pdf:4:1:0"),
    (("What is the minimum cooling-off period before trading can begin under a "
     "pre-approved trading plan?"),
     "pit_2015", "5", "2", "threshold", "medium", "pit_2015.pdf:5:2:1"),
    ("What was repealed by the PIT Regulations, 2015?",
     "pit_2015", "12", "1-2", "obligation", "hard", "pit_2015.pdf:12:1-2:0"),
    ("Who may formulate a trading plan and who must approve it?",
     "pit_2015", "5", "1", "obligation", "medium", "pit_2015.pdf:5:1:0"),
    # --- SAST (8) ---
    (("At what shareholding or voting rights threshold does an acquirer trigger the "
     "obligation to make an open offer?"),
     "sast_2011", "3", "1", "threshold", "easy", "sast_2011.pdf:3:1:0"),
    (("How much can an acquirer already holding between 25% and the maximum permissible "
     "non-public shareholding acquire in a financial year without triggering an open "
     "offer?"),
     "sast_2011", "3", "2", "threshold", "hard", "sast_2011.pdf:3:2:0"),
    (("What is the minimum size of an open offer that must be made under regulations 3 "
     "and 4 of the SAST Regulations?"),
     "sast_2011", "7", "1", "threshold", "medium", "sast_2011.pdf:7:1:0"),
    ("When must the public announcement of an open offer be made?",
     "sast_2011", "13", "1", "deadline", "medium", "sast_2011.pdf:13:1:0"),
    ("Can a wilful defaulter make a public announcement of an open offer?",
     "sast_2011", "6A", None, "obligation", "hard", "sast_2011.pdf:6A:None:0"),
    (("What must an acquirer do simultaneously with filing the draft letter of offer "
     "with the Board?"),
     "sast_2011", "18", "1", "obligation", "medium", "sast_2011.pdf:18:1:0"),
    ("How is 'volume weighted average price' defined under the SAST Regulations?",
     "sast_2011", "2", "2", "definition", "easy", "sast_2011.pdf:2:2:28"),
    (("What must an acquirer do if there is a shortfall in the escrow account "
     "maintained for an open offer?"),
     "sast_2011", "17", "7", "obligation", "hard", "sast_2011.pdf:17:7:0"),
    # --- IA (6) ---
    ("What must a person obtain before acting as an investment adviser?",
     "ia_2013", "3", "1", "obligation", "easy", "ia_2013.pdf:3:1:0"),
    (("What duty does an investment adviser owe to its clients regarding conflicts of "
     "interest?"),
     "ia_2013", "15", "1-2", "obligation", "easy", "ia_2013.pdf:15:1-2:0"),
    ("For how long must an investment adviser preserve its records?",
     "ia_2013", "19", "2", "deadline", "easy", "ia_2013.pdf:19:2:0"),
    ("What records must an investment adviser maintain about its clients?",
     "ia_2013", "19", "1", "obligation", "medium", "ia_2013.pdf:19:1:0"),
    ("Can an individual investment adviser provide distribution services?",
     "ia_2013", "22", "1-2", "obligation", "medium", "ia_2013.pdf:22:1-2:0"),
    (("How often must an investment adviser conduct a compliance audit, and who can "
     "perform it?"),
     "ia_2013", "19", "3", "deadline", "medium", "ia_2013.pdf:19:3:0"),
    # --- RA (6) ---
    ("What must a person obtain before acting as a research analyst?",
     "ra_2014", "3", "1", "obligation", "easy", "ra_2014.pdf:3:1:0"),
    ("For how long must a research analyst preserve its records?",
     "ra_2014", "25", "2", "deadline", "easy", "ra_2014.pdf:25:2:0"),
    ("What records must a research analyst maintain?",
     "ra_2014", "25", "1", "obligation", "medium", "ra_2014.pdf:25:1:0"),
    (("What is required regarding the personal trading activities of individuals "
     "employed as research analysts?"),
     "ra_2014", "16", "1-2", "obligation", "medium", "ra_2014.pdf:16:1-2:0"),
    (("Can a research analyst trade in a security contrary to their own published "
     "recommendation on it?"),
     "ra_2014", "16", "3-4", "obligation", "medium", "ra_2014.pdf:16:3-4:0"),
    (("What must a research analyst ensure about the facts used in its research "
     "reports?"),
     "ra_2014", "20", "1-2", "obligation", "medium", "ra_2014.pdf:20:1-2:0"),
]

# 10 paraphrased questions, deliberately avoiding the regulation's own defined
# terms/wording, testing whether dense retrieval can bridge the gap.
PARAPHRASED = [
    (("If a company's board decides something big is happening, how soon do they have "
     "to tell the public?"),
     "lodr_2015", "30", "1-2", "deadline", "medium", "lodr_2015.pdf:30:1-2:0"),
    (("Is someone who knows a juicy company secret before it's public allowed to tip "
     "off a friend?"),
     "pit_2015", "3", "1", "obligation", "medium", "pit_2015.pdf:3:1:0"),
    (("How big a stake can someone buy in a company before they're forced to offer to "
     "buy out other shareholders?"),
     "sast_2011", "3", "1", "threshold", "medium", "sast_2011.pdf:3:1:0"),
    ("How long does a financial advisor have to hang on to their client paperwork?",
     "ia_2013", "19", "2", "deadline", "easy", "ia_2013.pdf:19:2:0"),
    (("What's the least number of times a company's board needs to get together each "
     "year?"),
     "lodr_2015", "17", "2", "deadline", "medium", "lodr_2015.pdf:17:2:0"),
    ("Who's in charge of making sure a listed company follows the rules day to day?",
     "lodr_2015", "6", "1", "obligation", "medium", "lodr_2015.pdf:6:1:0"),
    ("How fast does a company have to sort out a shareholder's complaint?",
     "lodr_2015", "13", "1-2", "deadline", "easy", "lodr_2015.pdf:13:1-2:0"),
    (("Is it okay for someone giving stock tips for a living to also earn commissions "
     "from selling the products they're recommending?"),
     "ia_2013", "22", "1-2", "obligation", "hard", "ia_2013.pdf:22:1-2:0"),
    (("If a stock research writer publishes a 'buy' call, can they turn around and "
     "sell their own shares against it?"),
     "ra_2014", "16", "3-4", "obligation", "medium", "ra_2014.pdf:16:3-4:0"),
    (("What's the smallest slice of a company's stock a buyer has to offer for, once "
     "they're required to make a buyout offer?"),
     "sast_2011", "7", "1", "threshold", "hard", "sast_2011.pdf:7:1:0"),
]

# 5 unanswerable / out-of-scope questions.
UNANSWERABLE = [
    "What is the GST rate applicable to mutual fund management fees?",
    "What is the current repo rate set by the Reserve Bank of India?",
    "How do I file my income tax return as a salaried employee in India?",
    "What are the RBI's eligibility criteria for a home loan?",
    "What is the procedure for registering a trademark in India?",
]


def main() -> None:
    rows = []
    qid = 0
    for question, reg, reg_no, sub_reg, qtype, difficulty, chunk_id in ANSWERABLE:
        qid += 1
        rows.append(
            {
                "id": f"q{qid:03d}",
                "question": question,
                "gold_reg": f"{reg}:{reg_no}",
                "gold_sub_reg": sub_reg,
                "difficulty": difficulty,
                "type": qtype,
                "paraphrased": False,
                "chunk_id": chunk_id,
            }
        )
    for question, reg, reg_no, sub_reg, qtype, difficulty, chunk_id in PARAPHRASED:
        qid += 1
        rows.append(
            {
                "id": f"q{qid:03d}",
                "question": question,
                "gold_reg": f"{reg}:{reg_no}",
                "gold_sub_reg": sub_reg,
                "difficulty": difficulty,
                "type": qtype,
                "paraphrased": True,
                "chunk_id": chunk_id,
            }
        )
    for question in UNANSWERABLE:
        qid += 1
        rows.append(
            {
                "id": f"q{qid:03d}",
                "question": question,
                "gold_reg": None,
                "gold_sub_reg": None,
                "difficulty": "medium",
                "type": "out_of_scope",
                "paraphrased": False,
                "chunk_id": None,
            }
        )

    assert len(rows) == 60, f"expected 60 questions, got {len(rows)}"

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVAL_DIR / "questions_draft.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} questions to {out_path}")


if __name__ == "__main__":
    main()
