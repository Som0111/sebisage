# Answer Samples — Phase 4.4 Human Spot-Check

For each answer: mark ✅ correct, ⚠️ partially correct, or ❌ wrong directly below the answer, then tell Claude Code "spot-check done".


---

## q019 (deadline, easy)

**Question:** Within how many days must a newly appointed key managerial personnel disclose their securities holdings?

**Gold:** `pit_2015:7` sub_reg `1`

**Answer:**

Every person upon appointment as a key managerial personnel must disclose their holding of securities of the company to the company within seven days of such appointment [1].

Source: [1]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 935, 'output_tokens': 36} | **Latency:** 22025ms

**Cited chunk text:**

- `pit_2015.pdf:7:1:0`: Initial Disclosures.  
(a). 
 
 
(b). 
Every person on appointment as a key managerial personnel or a director of the 
company or upon becoming a promoter or member of the promoter group shall 
disclose his holding of securities of the company as on the date of appointment or 
becoming a promoter, to the company within seven days of such appointment or 
becoming a promoter.


**Human mark:** _(✅)_


---

## q039 (deadline, medium)

**Question:** How often must an investment adviser conduct a compliance audit, and who can perform it?

**Gold:** `ia_2013:19` sub_reg `3`

**Answer:**

An investment adviser must conduct a yearly audit regarding compliance with the regulations [1]. The audit must be performed by a member of the Institute of Chartered Accountants of India, the Institute of Company Secretaries of India, or the Institute of Cost Accountants of India [1].

Source: [1]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 697, 'output_tokens': 58} | **Latency:** 4055ms

**Cited chunk text:**

- `ia_2013.pdf:19:3:0`: An investment adviser shall conduct yearly audit in respect of compliance with these 
regulations from a member of Institute of Chartered Accountants of India or Institute of 
Company Secretaries of India or Institute of Cost Accountants of India and submit 
a report of the same as may be specified by the Board. 
 
Website.


**Human mark:** _(✅)_


---

## q035 (obligation, easy)

**Question:** What duty does an investment adviser owe to its clients regarding conflicts of interest?

**Gold:** `ia_2013:15` sub_reg `1-2`

**Answer:**

An investment adviser must act in a fiduciary capacity towards its clients and disclose all conflicts of interest as and when they arise [1]. It must disclose to the client its holdings or positions in the financial products or securities that are the subject matter of the advice [2]. Additionally, the adviser must disclose any actual or potential conflicts of interest arising from any connection to or association with any product or security issuer, including any material information or facts that might compromise its objectivity or independence [2]. If investment advisory activities conflict with other activities, this must also be disclosed to the client [3]. Furthermore, an investment adviser should try to avoid conflicts of interest as far as possible; when they cannot be avoided, appropriate disclosures must be made and clients must be fairly treated [4].

Source: [1], [2], [3], [4]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 1292, 'output_tokens': 168} | **Latency:** 3718ms

**Cited chunk text:**

- `ia_2013.pdf:15:1-2:0`: An investment adviser shall act in a fiduciary capacity towards its clients and 
shall disclose all conflicts of interests as and when they arise.

An investment adviser shall not receive any consideration by way of 
remuneration or compensation or in any other form from any person other than the 
client being advised, in respect of the underlying products or securities for which advice 
is provid...

- `ia_2013.pdf:18:4-5:0`: An investment adviser shall disclose to the client its holding or position, if any, in 
the financial products or securities which are subject matter of advice.

An investment adviser shall disclose to the client any actual or potential conflicts 
of interest arising from any connection to or association with any issuer of products/

securities, including any material information or facts that mig...

- `ia_2013.pdf:15:5:0`: An investment adviser shall ensure that in case of any conflict of interest of the 
investment advisory activities with other activities, such conflict of interest shall be 
disclosed to the client.  
                                                                                                                                                        
61 Clause (f) renumbered as (h) by the SEBI (I...

- `ia_2013.pdf:30A:None:23`: [Regulation 30A] of its business activities. 4. Information about clients An investment adviser shall seek from its clients, information about their financial situation, investment experience and investment objectives relevant to the services to be provided and maintain confidentiality of such information. 5. Information to its clients An investment adviser shall make adequate disclosures of relev...


**Human mark:** _(✅)_


---

## q047 (obligation, medium, paraphrased)

**Question:** Is someone who knows a juicy company secret before it's public allowed to tip off a friend?

**Gold:** `pit_2015:3` sub_reg `1`

**Answer:**

No insider is allowed to communicate, provide, or allow access to any unpublished price sensitive information to any person, including other insiders, unless that communication is for legitimate purposes, the performance of duties, or the discharge of legal obligations [1], [3]. Insiders possessing such information must handle it with care and deal with it strictly on a need-to-know basis [1], [3]. 

Source: [1], [3]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 1246, 'output_tokens': 90} | **Latency:** 2997ms

**Cited chunk text:**

- `pit_2015.pdf:3:1:0`: No insider shall communicate, provide, or allow access to any unpublished price 
sensitive information, relating to a company or securities listed or proposed to be listed, to any 
person including other insiders except where such communication is in furtherance of legitimate 
purposes, performance of duties or discharge of legal obligations.  
 
NOTE: 
This provision is intended to cast an obliga...

- `pit_2015.pdf:5C:1:0`: No insider shall communicate, provide, or allow access to any unpublished price 
sensitive information to any person including other insiders except where such 
communication is in furtherance of legitimate purposes, performance of duties or discharge 
of legal obligations. 
NOTE: 
This provision is intended to cast an obligation on all insiders who are 
essentially persons in possession of unpubl...


**Human mark:** _(✅)_


---

## q030 (obligation, hard)

**Question:** Can a wilful defaulter make a public announcement of an open offer?

**Gold:** `sast_2011:6A` sub_reg `None`

**Answer:**

No person who is a wilful defaulter shall make a public announcement of an open offer for acquiring shares or enter into any transaction that would attract the obligation to make a public announcement of an open offer [1]. However, a wilful defaulter is not prohibited from making a competing offer if another person has made an open offer for acquiring shares of the target company [1].

Source: [1]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 764, 'output_tokens': 82} | **Latency:** 2756ms

**Cited chunk text:**

- `sast_2011.pdf:6A:None:0`: Notwithstanding anything contained in these regulations, no person who is a wilful 
defaulter shall make a public announcement of an open offer for acquiring shares or enter 
into any transaction that would attract the obligation to make a public announcement of 
an open offer for acquiring shares under these regulations: 
 
Provided that this regulation shall not prohibit the wilful defaulter fro...


**Human mark:** _(✅)_


---

## q023 (threshold, medium)

**Question:** What is the minimum cooling-off period before trading can begin under a pre-approved trading plan?

**Gold:** `pit_2015:5` sub_reg `2`

**Answer:**

To get the benefit of a trading plan, a cool-off period of one hundred and twenty calendar days from the public disclosure of the plan is necessary before trading can commence on behalf of the insider [1].

Source: [1]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 1642, 'output_tokens': 48} | **Latency:** 3744ms

**Cited chunk text:**

- `pit_2015.pdf:5:2:1`: [Regulation 5] (i) 
not entail commencement of trading on behalf of the insider earlier than one 
hundred and twenty calendar days from the public disclosure of the plan;

NOTE: 
It is intended that to get the benefit of a trading plan, a cool-off period of 
one hundred and twenty calendar days is necessary. Companies declare their 
results quarterly and there exists a trading restriction, in term...


**Human mark:** _(✅)_


---

## q027 (threshold, hard)

**Question:** How much can an acquirer already holding between 25% and the maximum permissible non-public shareholding acquire in a financial year without triggering an open offer?

**Gold:** `sast_2011:3` sub_reg `2`

**Answer:**

An acquirer already holding 25% or more but less than the maximum permissible non-public shareholding cannot acquire additional shares or voting rights entitling them to exercise more than five per cent of the voting rights within any financial year without making a public announcement of an open offer [2].

Source: [2]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 1420, 'output_tokens': 65} | **Latency:** 3737ms

**Cited chunk text:**

- `sast_2011.pdf:3:2:0`: No acquirer, who together with persons acting in concert with him, has 
acquired and holds in accordance with these regulations shares or voting rights 
in a target company entitling them to exercise twenty-five per cent or more of 
the voting rights in the target company but less than the maximum permissible 
non-public shareholding, shall acquire within any financial year additional

shares or v...


**Human mark:** _(✅)_


---

## q057 (out_of_scope, medium)

**Question:** What is the current repo rate set by the Reserve Bank of India?

**Gold:** `None` sub_reg `None`

**Answer:**

INSUFFICIENT_CONTEXT

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 562, 'output_tokens': 6} | **Latency:** 3844ms

**Cited chunk text:** (none)


**Human mark:** _(✅)_


---

## q016 (definition, easy)

**Question:** How do the PIT Regulations define an 'insider'?

**Gold:** `pit_2015:2` sub_reg `1`

**Answer:**

Under the PIT Regulations, an "insider" is defined as any person who is a connected person, or is in possession of or has access to unpublished price sensitive information [1]. Under Regulation 5B, it is also defined as any person who is a connected person or is in possession of or has access to unpublished price sensitive information pertaining to a scheme [2].

Source: [1], [2]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 837, 'output_tokens': 84} | **Latency:** 80248ms

**Cited chunk text:**

- `pit_2015.pdf:2:1:10`: [Regulation 2] (g) 
"insider" means any person who is: 
 
i)  
a connected person; or  
 
ii)  
in possession of or having access to unpublished price sensitive 
information;  
 
NOTE:    Since "generally available information" is defined, it is intended that anyone 
in possession of or having access to unpublished price sensitive information should be 
considered as an "insider" regardless of the...

- `pit_2015.pdf:5B:1:17`: [Regulation 5B] (d) “insider” means any person who is: 
i. a connected person; or 
ii.in possession of or having access to unpublished price sensitive information 
pertaining to a scheme;


**Human mark:** _(✅)_


---

## q010 (penalty, hard)

**Question:** What happens if a listed entity fails to pay a fine imposed on it by the stock exchange?

**Gold:** `lodr_2015:99` sub_reg `None`

**Answer:**

If a listed entity fails to pay a fine imposed by a recognised stock exchange within the specified period and after receiving a written notice, the stock exchange may initiate action [1].

Source: [1]

**Grounded:** True (flags: none)

**Usage:** {'input_tokens': 800, 'output_tokens': 41} | **Latency:** 32741ms

**Cited chunk text:**

- `lodr_2015.pdf:99:None:0`: If listed entity fails to pay any fine imposed on it within such period as specified from 
time to time, by the recognised stock exchange(s), after a notice in writing has been 
served on it, the stock exchange may initiate action.

CHAPTER XI-A 
POWER TO RELAX STRICT ENFORCEMENT OF THE REGULATIONS 
Exemption from enforcement of the regulations in special cases.


**Human mark:** _(✅)_
