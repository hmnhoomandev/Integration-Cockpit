from datetime import date
from unittest import TestCase
from unittest.mock import patch

from cockpit import ai, data, predict, redact, rules


class PredictionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        db = data.connect(':memory:')
        index,_ = data.load_files(db,data.seed(data.MONTHS[1]).values(),data.MONTHS[1],'synthetic')
        cls.cases = rules.evaluate(*data.get_snapshot(db,index))
        db.close()
        cls.model = predict.Model(cls.cases,date(2026,10,31))

    def test_model_beats_the_average_on_held_out_cases(self):
        v = self.model.validation
        self.assertGreater(v['n'],200)
        self.assertGreater(v['auc'],.7)
        self.assertLess(v['brier'],v['baseline_brier'])

    def test_protected_traits_are_not_features(self):
        for trait in ('nationality','mother_tongue','gender','Nationalität Land','Muttersprache','Geschlecht'):
            self.assertNotIn(trait,predict.FEATURES)

    def test_only_open_a1_cases_get_a_forecast(self):
        open_case = next(c for c in self.cases if c['goals'][0]['state']=='ontrack')
        done_case = next(c for c in self.cases if c['goals'][0]['state']=='achieved')
        result = self.model.explain(open_case)
        self.assertTrue(0<result['probability']<1)
        self.assertLessEqual(len(result['factors']),3)
        self.assertIsNone(self.model.explain(done_case))


class ShieldTests(TestCase):
    SAMPLE = ('ZEMIS-Nr: 12345678\nName: Amina Beispiel\nGeburtsdatum 08.04.1987, AHV 756.1234.5678.97\n'
              'Adresse: Musterstrasse 12, 3027 Bern\nTel +41 79 555 12 34, amina@example.org\nFrau Beispiel, Klientin DEMO-00001.')

    def test_personal_details_are_masked_before_leaving(self):
        masked,counts = redact.mask(self.SAMPLE)
        for secret in ('Amina','Beispiel','08.04.1987','756.1234','Musterstrasse','3027 Bern','555 12 34','amina@','DEMO-00001','12345678'):
            self.assertNotIn(secret,masked)
        self.assertEqual(redact.leaks(masked),[])
        self.assertTrue({'name','date','ahv','address','phone','email','case_id'} <= set(counts))

    def test_nothing_is_sent_when_switched_off_or_when_masking_fails(self):
        with patch.dict('os.environ',{'COCKPIT_AI':''}):
            answer,report = ai.ask(0,'Summarise',self.SAMPLE)
        self.assertIsNone(answer)
        self.assertEqual(report['state'],'off')
        self.assertNotIn('Amina',report['sent'])
        with patch.dict('os.environ',{'COCKPIT_AI':'claude'}), patch.object(redact,'mask',lambda text,extra=():(text,{})):
            answer,report = ai.ask(0,'Summarise',self.SAMPLE)
        self.assertEqual(report['state'],'blocked')
        self.assertIsNone(answer)
