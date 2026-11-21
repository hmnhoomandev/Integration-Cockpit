from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from zipfile import ZipFile

from cockpit import data, insights, intake, rules, ui, xlsx


class SnapshotTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = data.connect(':memory:')
        cls.first, cls.second = [data.load_files(cls.db,data.seed(month).values(),month,'synthetic')[0] for month in data.MONTHS]

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_all_contracts_and_idempotency(self):
        for month, identifier in zip(data.MONTHS,(self.first,self.second)):
            generated = data.seed(month)
            self.assertEqual(set(generated),set(data.SCHEMA))
            for key,blob in generated.items():
                self.assertEqual(next(xlsx.read(blob))[1],data.SCHEMA[key]['headers'])
            self.assertEqual(data.load_files(self.db,generated.values(),month,'synthetic'),(identifier,True))

    def test_reordered_columns_and_backup(self):
        asof = data.MONTHS[-1]
        books = data.seed(asof)
        reordered = [list(reversed(cells + [None]*(7-len(cells)))) for _,cells,_ in xlsx.read(books['events'])]
        books['events'] = xlsx.write({'events':reordered})
        with TemporaryDirectory() as directory:
            path = Path(directory)/'backup.sqlite'
            db = data.connect(':memory:')
            try:
                identifier,_ = data.load_files(db,books.values(),asof,'synthetic')
                data.backup(db,path)
                with self.assertRaises(FileExistsError):
                    data.backup(db,path)
                restored = data.connect(path)
                try:
                    snap, rows = data.get_snapshot(restored,identifier)
                    self.assertEqual(rules.evaluate(snap,rows)[0]['goals'][0]['state'],'achieved')
                finally:
                    restored.close()
            finally:
                db.close()

    def test_invalid_batch_does_not_publish(self):
        books = data.seed(data.MONTHS[0])
        spec = data.SCHEMA['events']['headers']
        books['events'] = xlsx.write({'events':[spec,['SYN-UNKNOWN','UNKNOWN','Aufenthalt (Einreise)','2025-01-01']]})
        with self.assertRaises(data.ImportFailure) as ctx:
            data.load_files(self.db,books.values(),'2026-11-01','local')
        self.assertIn(('events',2,'unresolved_or_conflicting_person'),ctx.exception.errors)
        self.assertEqual(data.get_snapshot(self.db)[0]['id'],self.second)

    def test_a1_monthly_change_and_household_reconciliation(self):
        snapshots = [data.get_snapshot(self.db,s) for s in (self.first,self.second)]
        old,new = (rules.evaluate(snapshot,rows) for snapshot,rows in snapshots)
        self.assertEqual(old[0]['goals'][0]['state'],'risk')
        goal = new[0]['goals'][0]
        self.assertEqual((goal['state'],goal['achieved'],goal['deadline']),
                         ('achieved',date(2026,10,12),date(2026,10,16)))
        self.assertTrue(any(case['goals'][2]['state']=='achieved' for case in new))
        expected = len({c['home'] for c in new if c['goals'][2]['state']!='na'})
        self.assertEqual(sum(rules.counts(new,2).values()),expected)

    def test_excel_output_filters_and_locale(self):
        snap,rows = data.get_snapshot(self.db,self.second)
        cases = rules.evaluate(snap,rows)
        for lang in range(3):
            blob = xlsx.write(ui.export(lang,snap,cases,'judge'))
            with ZipFile(BytesIO(blob)) as workbook:
                self.assertIsNone(workbook.testzip())
                xml = workbook.read('xl/worksheets/sheet3.xml').decode()
                self.assertIn('DEMO-00001',xml)
                self.assertIn('2026-10-12',xml)
                self.assertIn('autoFilter',xml)
                self.assertIn(ui.tr(lang,'attained'),xml)
        with ZipFile(BytesIO(xlsx.write(ui.export(0,snap,cases,'manager')))) as workbook:
            self.assertFalse(any(b'DEMO-00001' in workbook.read(name) for name in workbook.namelist()))

    def test_scenario_does_not_mutate_baseline_and_payments_are_corroborated(self):
        snap,rows = data.get_snapshot(self.db,self.second)
        baseline = rules.evaluate(snap,rows)
        trial = rules.evaluate(snap,rows,candidate=True)
        self.assertEqual(baseline[0]['goals'][0],trial[0]['goals'][0])
        self.assertEqual(baseline[0]['goals'][1]['deadline'],date(2028,6,30))
        self.assertEqual(trial[0]['goals'][1]['deadline'],date(2028,10,16))
        self.assertEqual(trial[0]['goals'][2]['state'],'review')
        verified,unconfirmed,_ = rules.payments(baseline)[0]
        self.assertGreater(verified,0)
        self.assertGreater(unconfirmed,0)
        self.assertEqual(verified+unconfirmed,rules.counts(baseline,0)['achieved'])
        self.assertEqual(rules.evaluate(snap,rows),baseline)

    def test_a1_totals_reconcile_by_worker_and_entry_year(self):
        snap, rows = data.get_snapshot(self.db,self.second)
        cases = rules.evaluate(snap,rows)
        for lang in range(3):
            tabs = ui.export(lang,snap,cases,'judge')
            _, total = tabs[ui.tr(lang,'control_totals')]
            self.assertEqual(total[0],144)
            self.assertEqual(total[0],sum(total[1:4]))
            self.assertEqual(total[1],sum(total[4:7]))
            self.assertEqual(total[7],sum(total[8:10]))
            for key in ('worker','year'):
                rows = tabs[ui.tr(lang,key)][1:]
                self.assertEqual([sum(col) for col in zip(*(row[1:] for row in rows))],total)

    def test_phase4_work_and_household_fixture(self):
        month = data.PHASE4_MONTH
        db = data.connect(':memory:')
        try:
            index,_ = data.load_files(db,data.seed(month).values(),month,'synthetic')
            snapshot, rows = data.get_snapshot(db,index)
            cases = rules.evaluate(snapshot,rows)
        finally:
            db.close()
        education, gap, unknown = cases[:3]
        self.assertEqual(education['goals'][1]['reason'],'education')
        self.assertEqual(gap['goals'][1]['reason'],'employment_gap')
        self.assertEqual(gap['goals'][1]['earliest'],date(2026,10,2))
        self.assertEqual(len(gap['goals'][1]['evidence']),2)
        self.assertEqual(gap['goals'][2]['reason'],'membership_reset')
        self.assertEqual(gap['goals'][2]['period_start'],date(2026,6,1))
        self.assertEqual(education['goals'][2],gap['goals'][2])
        self.assertEqual(unknown['goals'][2]['reason'],'coverage_unknown')
        self.assertEqual(education['reference_end'],date(2030,10,16))
        self.assertEqual(education['transition_end'],date(2028,10,16))
        self.assertEqual(education['goals'][1]['deadline'],date(2028,6,30))

    def test_local_import_household_coverage_conservative(self):
        with TemporaryDirectory() as directory:
            db=data.connect(Path(directory)/'data.sqlite')
            try:
                idx,_=data.load_files(db,data.seed(data.MONTHS[-1]).values(),data.MONTHS[-1],'local')
                snapshot,rows=data.get_snapshot(db,idx)
                self.assertTrue(all(c['goals'][2]['state'] in ('review','na') for c in rules.evaluate(snapshot,rows)))
            finally:
                db.close()


class RulesTests(TestCase):
    def test_calendar_and_excel_epochs(self):
        self.assertEqual(rules.months(date(2024,2,29),36),date(2027,2,28))
        self.assertEqual(xlsx.excel_date('29.02.2024'),date(2024,2,29))
        self.assertEqual(xlsx.excel_date(61.0),date(1900,3,1))
        self.assertEqual(xlsx.excel_date(1.0,True),date(1904,1,2))
        with self.assertRaises(ValueError):
            xlsx.excel_date(60.0)

    def test_education_and_no_parallel_work_summing(self):
        def job(start,end,percent,line):
            return {'Von':start,'Bis':end,'Pensum %':percent,'Erwerbsstatus':'1. Arbeitsmarkt','_line':line}
        start,date_end = date(2025,1,1),date(2026,10,31)
        tables = {'work':[job('2025-01-01',None,40,2),job('2025-01-01',None,35,3)],'education':[]}
        self.assertIsNone(rules.goal2(tables,date_end,start,date_end)['achieved'])
        tables['work'] = [job('2025-01-01','2025-03-31',60,2),job('2025-04-02','2025-05-30',70,3)]
        self.assertIsNone(rules.goal2(tables,date_end,start,date_end)['achieved'])
        tables['education'] = [{'Start':'2025-05-01','Art':'Sek II','_line':2}]
        self.assertEqual(rules.goal2(tables,date_end,start,date_end)['achieved'],date(2025,5,1))
        tables['work'] = [job('2025-01-01','2025-07-01',60,2)]
        tables['education'] = []
        self.assertEqual(rules.goal2(tables,date_end,start,date_end)['achieved'],date(2025,7,1))

    def test_future_wrong_language_and_unknown_certificate(self):
        today = date(2026,10,1)
        base = {'Art':'Zertifizierung','Sprachniveau':'A2','Datum Erreichung':'2025-10-01','_line':2}
        rows = {'language':[base|{'Sprache':'Französisch','Bemerkungen':'fide'},
                             base|{'Sprache':'Deutsch','Bemerkungen':'fide','Datum Erreichung':'2027-10-01'}],'official':[]}
        self.assertEqual(rules.goal1({},date(2024,1,1),today,rows)['reason'],'missing_proof')
        rows['language'].append(base|{'Sprache':'Deutsch'})
        self.assertEqual(rules.goal1({},date(2024,1,1),today,rows)['state'],'review')

    def test_no_assistance_flag_and_unrecognized_support_type(self):
        cutoff = date(2026,10,31)
        members = [{'Dossierperson Von':'2024-08-01','_line':2}]
        support = {'Finanzielle Unterstützung Gültig von':'2025-06-01','_line':2}
        absent = rules.goal3('fixture',members,[support|{'Unterstützung':'Keine Unterstützung'}],cutoff,cutoff,True)
        self.assertEqual(absent['achieved'],date(2025,8,1))
        unknown = rules.goal3('fixture',members,[support|{'Unterstützung':'other'}],cutoff,cutoff,True)
        self.assertEqual(unknown['state'],'review')

    def test_a1_deadline_and_undated_official_entry(self):
        entry, deadline = date(2023,10,16),date(2026,10,16)
        tables = {'language':[],'official':[]}
        due = rules.goal1({},entry,deadline,tables)
        self.assertEqual((due['state'],due['due']),('risk',True))
        self.assertEqual(rules.goal1({},entry,date(2026,10,17),tables)['state'],'overdue')
        tables['official'].append({'Art':'Sprachniveau A1','Erreicht am':None,'_line':2})
        review = rules.goal1({},entry,deadline,tables)
        self.assertEqual((review['state'],review['official_undated']),('review',True))
        tables['language'].append({'Art':'Zertifizierung','Sprachniveau':'A1','Sprache':'Deutsch',
                                   'Bemerkungen':'fide.','Datum Erreichung':'2026-10-16','_line':3})
        computed = rules.goal1({},entry,deadline,tables)
        self.assertEqual((computed['state'],computed['reason']),('achieved','proof_difference'))

    def test_a1_age_and_status_boundaries(self):
        now = date(2026,10,16)
        start = date(2025,1,1)
        args = start,None,set(),start,now
        self.assertEqual(rules.a1_scope('VA',date(2010,10,16),*args),'scope_in')
        self.assertEqual(rules.a1_scope('VA',date(2010,10,17),*args),'scope_out')
        self.assertEqual(rules.a1_scope('VA+7',date(2010,10,16),*args),'scope_review')
        self.assertEqual(rules.a1_scope('S',date(2010,10,16),*args),'scope_out')

    def test_household_departure_restarts_period_and_missing_cutoff_is_review(self):
        now, end = date(2026,8,31),date(2028,8,31)
        members = [{'Dossierperson Von':'2024-01-01','_line':2},
                   {'Dossierperson Von':'2024-01-01','Dossierperson Bis':'2026-06-30','_line':3}]
        goal = rules.goal3('demo',members,[],end,now,True)
        self.assertEqual((goal['period_start'],goal['earliest']),(date(2026,7,1),date(2027,7,1)))
        self.assertEqual(rules.goal3('demo',members,[],None,now,True)['reason'],'household_end_unknown')
        self.assertEqual(rules.goal3('demo',members,[],end,now,False)['state'],'review')

    def test_zemis_distinguishes_no_overlap_from_unverified_employer_or_dates(self):
        fed = {'Arbeitsbeginn':'2026-01-01','Verpflichtet bis':'2026-03-01','Betrieb':'Demo','_line':2}
        job = {'Von':'2026-02-01','Arbeitgeber Name':'demo','_line':5}
        asof = '2026-10-31'
        self.assertEqual(rules.zemis_reconcile([fed],[job],asof),[])
        self.assertEqual(rules.zemis_reconcile([fed],[],asof),[(2,'zemis_no_overlap',[])])
        self.assertEqual(rules.zemis_reconcile([fed],[job|{'Von':None}],asof),[(2,'zemis_dates_unknown',[])])
        self.assertEqual(rules.zemis_reconcile([fed],[job|{'Arbeitgeber Name':'other'}],asof),[(2,'zemis_employer_unknown',[5])])

    def test_literal_excel_cells(self):
        book = xlsx.write({'test':[['Code'],['=HYPERLINK("secret")'],['0004']]})
        self.assertEqual([row[1][0] for row in xlsx.read(book)],['Code','=HYPERLINK("secret")','0004'])


class InsightTests(TestCase):
    def test_closed_gateway_and_citation_in_every_locale(self):
        for payload in ({'client':'CANARY-SECRET'},insights.RuleQuestion('CANARY-SECRET',0),insights.IntakeQuestion('CANARY-SECRET')):
            with self.assertRaisesRegex(ValueError,'privacy_policy_denied'):
                insights.gateway(payload)
        for index in range(3):
            answer = insights.gateway(insights.RuleQuestion('a1',index))
            self.assertIn('pp. 1–2',answer['source'])
            self.assertIn('A1',answer['text'])
            self.assertEqual(answer['mode'],'retrieval_only')

    def test_aggregate_suppression(self):
        cases = [{'entry':date(2024,1,1),'goals':[{'state':'achieved','deadline':date(2026,1,1)}]} for i in range(7)]
        self.assertEqual(rules.group_metrics(cases),[(2024,None,None)])
        self.assertEqual(insights.gateway(insights.AggregateQuestion('entry_cohort'),'2026-10-31',cases)['mode'],'insufficient')

    def test_release_suppresses_single_small_group_and_complementary_group(self):
        safe = ['achieved']*12+['overdue']*12
        rare = ['achieved']+['overdue']*13
        self.assertEqual(rules.suppress_partition({'large':safe,'small':rare}),{'large','small'})

    def test_analysis_fixture_and_visible_aggregate_citation(self):
        month = data.PHASE5_MONTH
        db = data.connect(':memory:')
        try:
            index,_ = data.load_files(db,data.seed(month).values(),month,'synthetic')
            snapshot,rows = data.get_snapshot(db,index)
            cases = rules.evaluate(snapshot,rows)
        finally:
            db.close()
        full_labels = data.phase5_categories(cases)
        self.assertEqual(data.phase5_categories(cases[20:40]),
                         {c['id']:full_labels[c['id']] for c in cases[20:40] if c['id'] in full_labels})
        cohorts,_,released = rules.analysis(cases,date.fromisoformat(month),'year')
        self.assertEqual([row[1] for row in cohorts],[160,160])
        answer = insights.gateway(insights.AggregateQuestion('entry_cohort'),month,cases)
        self.assertIn((answer['year'],answer['denominator'],answer['count']),[(y,n,k) for y,n,_,k,_ in released])
        for g in (1,2):
            results,_,_ = rules.analysis(cases,date.fromisoformat(month),goal_index=g)
            self.assertTrue(results)
            tabs = ui.analysis_export(1,snapshot,cases,'year',{},g)
            blob = xlsx.write(tabs)
            with ZipFile(BytesIO(blob)) as archive:
                self.assertFalse(any(b'DEMO-00001' in archive.read(n) or b'SYN-H' in archive.read(n) for n in archive.namelist()))

    def test_forecast_is_repeatable_and_uses_holdout(self):
        report = insights.backtest()
        self.assertEqual(report,insights.backtest())
        self.assertEqual(report['heldout'],12)
        self.assertLessEqual(report['lo'],report['est'])
        self.assertLessEqual(report['est'],report['hi'])
        self.assertEqual(insights.backtest([5,6]),{'mode':'insufficient'})

    def test_malformed_pdf(self):
        self.assertEqual(intake.suggest(b'CANARY-SECRET',{})['mode'],'manual')
