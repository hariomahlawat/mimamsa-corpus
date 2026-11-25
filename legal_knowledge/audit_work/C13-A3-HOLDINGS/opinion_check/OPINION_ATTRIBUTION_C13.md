# C13-A3 opinion-attribution check (multi-opinion judgments)

Gold built by the developer from author lines, running headers and bench composition (`gold/OPINION_GOLD_C13.csv`, evidence per row). **Not independent, not legally reviewed**; the coordinator should arrange an independent check. Developer-built gold also overlaps the judgments used while writing the opinion rules (in-sample).

## Opinion level

| Measure | Result |
| --- | --- |
| Gold opinions located (author match, start within 2 pages) | 47/48 |
| Binding class correct among located (COURT_SIDE vs NOT_COURT) | 39/47 |

| judgment | case | gold author | gold start | gold role | detected | detected class | result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| J-050c76ffc9421791 | Maneka Gandhi v UoI (1978) | BEG | p23 | concurring | OP1:lead@p23 | COURT_SIDE | OK |
| J-050c76ffc9421791 | Maneka Gandhi v UoI (1978) | CHANDRACHUD | p37 | concurring | OP2:concurring@p37 | COURT_SIDE | OK |
| J-050c76ffc9421791 | Maneka Gandhi v UoI (1978) | BHAGWATI | p43 | majority | OP3:separate@p43 | COURT_SIDE | OK |
| J-050c76ffc9421791 | Maneka Gandhi v UoI (1978) | KAILASAM | p114 | partly_dissenting | OP4:concurring@p114 | COURT_SIDE | WRONG_CLASS |
| J-050c76ffc9421791 | Maneka Gandhi v UoI (1978) | ORDER | p156 | court_order | OP5:court_order@p156 | COURT_SIDE | OK |
| J-09c67ba85addf433 | SC AOR Assn v UoI (NJAC 2015) | JAGDISH SINGH KHEHAR | p92 | majority | OP1:lead@p92 | COURT_SIDE | OK |
| J-09c67ba85addf433 | SC AOR Assn v UoI (NJAC 2015) | CHELAMESWAR | p514 | dissent | OP2:dissent@p514 | NOT_COURT | OK |
| J-09c67ba85addf433 | SC AOR Assn v UoI (NJAC 2015) | MADAN B. LOKUR | p622 | concurring | OP3:separate@p622 | COURT_SIDE | OK |
| J-09c67ba85addf433 | SC AOR Assn v UoI (NJAC 2015) | KURIAN | p942 | concurring | OP4:concurring@p942 | COURT_SIDE | OK |
| J-09c67ba85addf433 | SC AOR Assn v UoI (NJAC 2015) | ADARSH KUMAR GOEL | p963 | concurring | OP5:concurring@p963 | COURT_SIDE | OK |
| J-09c67ba85addf433 | SC AOR Assn v UoI (NJAC 2015) | ORDER | p1055 | court_order | OP6:court_order@p1055 | COURT_SIDE | OK |
| J-0af19b8f3bae094c | Virender Kumar v COAS (1994) | SAHAI | p3 | sole | OP1:sole@p3 | COURT_SIDE | OK |
| J-28f88d53cdcab798 | Secy MoD v (2009) | DALVEER BHANDARI | p5 | majority | OP1:lead@p5 | COURT_SIDE | OK |
| J-28f88d53cdcab798 | Secy MoD v (2009) | DR. MUKUNDAKAM SHARMA | p15 | concurring | OP2:separate@p15 | COURT_SIDE | OK |
| J-2b2db8ab38057018 | Express Newspapers v UoI (1985) | A.P. SEN | p30 | majority | OP1:lead@p30 | COURT_SIDE | OK |
| J-2b2db8ab38057018 | Express Newspapers v UoI (1985) | VENKATARAMIAH | p174 | concurring | OP2:separate@p174 | COURT_SIDE | OK |
| J-2b2db8ab38057018 | Express Newspapers v UoI (1985) | MISRA | p176 | concurring | OP3:concurring@p176 | COURT_SIDE | OK |
| J-3130322b6f533e0d | Joseph Shine v UoI (2018) | DIPAK MISRA | p39 | majority | OP1:lead@p39 | COURT_SIDE | OK |
| J-3130322b6f533e0d | Joseph Shine v UoI (2018) | R. F. NARIMAN | p74 | concurring | OP2:separate@p74 | COURT_SIDE | OK |
| J-3130322b6f533e0d | Joseph Shine v UoI (2018) | DR. D. Y. CHANDRACHUD | p100 | concurring | OP3:separate@p100 | COURT_SIDE | OK |
| J-3130322b6f533e0d | Joseph Shine v UoI (2018) | INDU MALHOTRA | p154 | concurring | OP4:separate@p154 | COURT_SIDE | OK |
| J-5c1c23b8ad57146f | Gene Campaign v UoI (2024) | SANJAY KAROL | p15 | split_opinion | OP1:split_opinion@p15 | NOT_COURT | OK |
| J-5c1c23b8ad57146f | Gene Campaign v UoI (2024) | NAGARATHNA | p110 | split_opinion | OP2:split_opinion@p110 | NOT_COURT | OK |
| J-5c1c23b8ad57146f | Gene Campaign v UoI (2024) | ORDER | p296 | court_order | OP3:court_order@p296 | COURT_SIDE | OK |
| J-83dd7117f2058cd3 | Madras Bar Assn v UoI (2014) | JAGDISH SINGH KHEHAR | p25 | majority | OP1:lead_majority@p25 | COURT_SIDE | OK |
| J-83dd7117f2058cd3 | Madras Bar Assn v UoI (2014) | R.F.NARIMAN | p319 | concurring | OP2:concurring@p319 | COURT_SIDE | OK |
| J-936a4cbfa08edd49 | UoI v V. Sriharan (2015) | FAKKIR MOHAMED IBRAHIM KALIFULLA | p15 | majority | OP1:lead_majority@p15 | COURT_SIDE | OK |
| J-936a4cbfa08edd49 | UoI v V. Sriharan (2015) | UDAY UMESH LALIT | p157 | dissent | OP2:concurring@p158 | COURT_SIDE | WRONG_CLASS |
| J-936a4cbfa08edd49 | UoI v V. Sriharan (2015) | ABHAY MANOHAR SAPRE | p234 | dissent | not detected | - | MISSED |
| J-936a4cbfa08edd49 | UoI v V. Sriharan (2015) | ORDER | p235 | court_order | OP3:court_order@p235 | COURT_SIDE | OK |
| J-96ce4a1a9cabc707 | Vivek Narayan Sharma v UoI (2023) | B. R. GAVAI | p31 | majority | OP1:lead@p31 | COURT_SIDE | OK |
| J-96ce4a1a9cabc707 | Vivek Narayan Sharma v UoI (2023) | NAGARATHNA | p145 | dissent | OP2:separate@p145 | COURT_SIDE | WRONG_CLASS |
| J-a7adc9ef913589cb | K.S. Puttaswamy (Aadhaar) v UoI (2019) | A. K. SIKRI | p132 | majority | OP1:lead@p132 | COURT_SIDE | OK |
| J-a7adc9ef913589cb | K.S. Puttaswamy (Aadhaar) v UoI (2019) | ASHOK BHUSHAN | p518 | concurring | OP2:separate@p518 | COURT_SIDE | OK |
| J-a7adc9ef913589cb | K.S. Puttaswamy (Aadhaar) v UoI (2019) | DR. D. Y. CHANDRACHUD | NOT_LOCATED_IN_TEXT | dissent | - | - | excluded |
| J-b20b4db0d2e9468f | S.R. Bommai v UoI (1994) | SAWANT | p68 | majority | OP1:lead@p68 | COURT_SIDE | OK |
| J-b20b4db0d2e9468f | S.R. Bommai v UoI (1994) | B.P. JEEVAN REDDY | p155 | majority | OP2:separate@p155 | COURT_SIDE | OK |
| J-b20b4db0d2e9468f | S.R. Bommai v UoI (1994) | K RAMASWAMY | p255 | concurring | OP3:separate@p255 | COURT_SIDE | OK |
| J-b20b4db0d2e9468f | S.R. Bommai v UoI (1994) | VERMA | p329 | partly_dissenting | OP4:separate@p329 | COURT_SIDE | WRONG_CLASS |
| J-b20b4db0d2e9468f | S.R. Bommai v UoI (1994) | AHMADI | p334 | partly_dissenting | OP5:concurring@p334 | COURT_SIDE | WRONG_CLASS |
| J-b20b4db0d2e9468f | S.R. Bommai v UoI (1994) | S. RATNAVEL PANDIAN | p354 | concurring | OP6:concurring@p354 | COURT_SIDE | OK |
| J-b69d2f6ca5e71571 | Supriyo v UoI (2023) | DR. DHANANJAYA Y CHANDRACHUD | p27 | minority | OP1:lead@p27 | COURT_SIDE | WRONG_CLASS |
| J-b69d2f6ca5e71571 | Supriyo v UoI (2023) | SANJAY KISHAN KAUL | p213 | minority | OP2:separate@p213 | COURT_SIDE | WRONG_CLASS |
| J-b69d2f6ca5e71571 | Supriyo v UoI (2023) | S. RAVINDRA BHAT | p224 | majority | OP3:separate@p224 | COURT_SIDE | OK |
| J-b69d2f6ca5e71571 | Supriyo v UoI (2023) | PAMIDIGHANTAM SRI NARASIMHA | p307 | concurring | OP4:dissent@p307 | NOT_COURT | WRONG_CLASS |
| J-bae31191140c5df6 | Parshotam Lal Dhingra v UoI (1957) | DAS | p5 | majority | OP1:lead_majority@p5 | COURT_SIDE | OK |
| J-bae31191140c5df6 | Parshotam Lal Dhingra v UoI (1957) | BOSE | p37 | dissent | OP2:dissent@p37 | NOT_COURT | OK |
| J-d9470d72b572e71d | UoI v R.P. Yadav (2000) | D.P. MOHAPATRA | p5 | majority | OP1:lead_majority@p5 | COURT_SIDE | OK |
| J-d9470d72b572e71d | UoI v R.P. Yadav (2000) | RUMA PAL | p13 | dissent | OP2:dissent@p13 | NOT_COURT | OK |

## Item level (holding-class items in the gold judgments)

| Measure | c12-holdings (frozen scope output) | c13 |
| --- | --- | --- |
| Holding-class items scored | 488 | 94 |
| Author attribution correct | 406/488 (83.2%) | 81/94 (86.2%) |
| Presented as the court's holding but gold opinion is dissent / minority / split | 159/488 (32.6%) | 6/94 (6.4%) |
| Items on an opinion's first page (scored leniently) | 15 | 10 |

Misattributed items per judgment (c13): J-936a4cbfa08edd49: 1, J-96ce4a1a9cabc707: 1, J-b20b4db0d2e9468f: 2, J-b69d2f6ca5e71571: 2

Misattributed items per judgment (c12): J-050c76ffc9421791: 23, J-5c1c23b8ad57146f: 24, J-936a4cbfa08edd49: 24, J-96ce4a1a9cabc707: 25, J-b20b4db0d2e9468f: 8, J-b69d2f6ca5e71571: 30, J-bae31191140c5df6: 15, J-d9470d72b572e71d: 10

C12 items flagged `opinion = dissent` are not counted as misattributed for C12 (it carried a dissent note).

