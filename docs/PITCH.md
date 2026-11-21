# Three-minute pitch

## Before you go on stage

- Sign in as the demo account. Set the language the jury speaks: DE or EN.
- In **Daten & Berichte**, load **30.09.2026**.
- Keep two tabs open: **Fallführung** and **DEMO-00001**.
- Close the terminal. Credentials must never appear on screen.

---

## 0:00–0:25 · The problem

> “ASD is paid when a person reaches an integration goal before ASD’s responsibility ends: A1 German, work or education, and a household free of social assistance. The evidence already exists, but it is spread over eleven Excel exports. Every month someone has to work out which deadline applies, whether the proof is there, and who needs a call. So we asked one question: **who should I contact this week, and why?**”

## 0:25–1:15 · The caseworker

*Show **Fallführung**, the “Diese Woche” box.*

> “This is the answer. 164 contacts, ranked by what a call can still change. Deadlines that can still be met come first. Next come goals that are reached but not yet recorded, because without the record ASD isn’t paid. Missed deadlines come last. Nationality and age play no part in the order.”

*Open **DEMO-00001**.*

> “A1 is due on 16 October, in 16 days. The next step is right at the top: register for a fide or telc exam. Below it, every result shows the Excel rows it came from.”

*Switch to the October snapshot in **Daten & Berichte** and reopen the case.*

> “One month later, the same eleven files come in again. A fide certificate dated 12 October has arrived, four days before the deadline, so the light turns green. But the official goal table doesn’t have it yet, so the cockpit says: record it, or the payment is lost.”

## 1:15–1:55 · Management

*Show **Übersicht**, the target and actual table.*

> “Level 1: per caseworker and per entry year, how many deadlines have passed and how many were met on time. These are exactly the totals in the Excel export.”

*Scroll to the group analysis and choose **Sprachkurs**.*

> “Level 2: what do people who make it have in common? In our demo data, people who start a language course within six months reach A1 on time in 73 % of cases. Those who start later reach it in 28 %. The uncertainty ranges don’t overlap. We say it plainly on screen: that is an association, not a proven cause. Groups smaller than eight are hidden, so nobody can be identified.”

*Switch **Demo-Rolle** to **Leitung**.*

> “Management sees totals only. The server enforces this, not just the screen.”

## 1:55–2:30 · Planning

*Switch back to **Demo-Konto** and open **Planung**.*

> “Payments: 103 goals are already reached but cannot be claimed yet, because the official record is missing. One click opens exactly those cases. The 2027 rule shortens responsibility from seven to five years: 544 people would leave earlier, and 25 goals would be overdue at once. Finally, ZEMIS shows 27 jobs that don’t match our records.”

## 2:30–3:00 · Trust and next step

*Open **Datenschutz** for two seconds, then click **Excel herunterladen**.*

> “All of this runs on one ASD computer. There is no cloud and no AI service, and the browser is technically blocked from loading anything external. The Excel goes straight back into today’s workflow, with Swiss dates and colour-coded results. Every button has a small ‘!’ that explains itself, in German, French and English.
>
> Next step: ASD confirms our reading of the rules, and we run one real month together, on ASD’s machine.”

---

## If the jury asks

- *Is the data real?* No. About 1,400 invented people. The patterns were planted on purpose and are listed in `docs/SOURCES.md`. Real data will give different numbers.
- *Is there AI in it?* The rules assistant retrieves approved, cited rule texts, and the forecast is validated on held-back months. No language model sees personal data.
- *What if a file is missing or broken?* The import is rejected, the last valid month stays, and a quality workbook names the file, row and reason.
- *Can ASD change a rule?* A1 and the responsibility periods are JSON policy files, so changing them needs no new code.
