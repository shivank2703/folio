"""Public disclosure checks: source identity, coverage boundaries and refusals."""
import copy
import unittest
from funds.data import load_funds, validate, coverage
from funds.answer import answer
from gen.guardrails import REFUSAL

class FundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.funds = {f['id']: f for f in load_funds()}

    def test_verified_public_snapshots(self):
        self.assertEqual([len(f['holdings']) for f in self.funds.values()], [62,26,500])
        selected = {r['company'] for f in self.funds.values() for r in f['holdings'] if r['eligible']}
        self.assertEqual(len(selected),28)
        self.assertNotIn(None,selected)
        for f in self.funds.values():
            self.assertEqual(sum(r['eligible'] for r in f['holdings']),10)

    def test_coverage_is_per_fund_and_requires_manifest(self):
        f=self.funds['kotak-manufacture']
        bel=next(r for r in f['holdings'] if r['isin']=='INE263A01024')
        self.assertEqual(bel['rank'],11)
        self.assertIsNone(coverage(bel,[{'company':'BEL'}]))
        sun=f['holdings'][0]
        self.assertIsNone(coverage(sun,[]))
        self.assertEqual(coverage(sun,[{'company':'SUNPHARMA'}]),{'company':'SUNPHARMA'})

    def test_incomplete_or_misranked_snapshot_rejected(self):
        for mutation in ('drop','rank','total'):
            f=copy.deepcopy(self.funds['hdfc-defence'])
            if mutation=='drop':f['holdings'].pop()
            elif mutation=='rank':f['holdings'][0]['rank']=2
            else:f['disclosed_total_pct']=90
            with self.assertRaises(ValueError):validate(f)

    def test_fact_citations_and_expense_definition(self):
        out=answer('What is the Direct expense ratio?',self.funds['hdfc-defence'])
        for expected in ['0.82%','Base expense ratio','page=29','2026-09-30']:
            self.assertIn(expected,out)

    def test_holdings_are_exact_and_source_referenced(self):
        f=self.funds['hdfc-defence']
        out=answer('What is the BEL weight?',f)
        self.assertIn('14.87%',out)
        self.assertIn('HDFCDFNFND row 9',out)
        self.assertIn('-0.60%',answer('What is the net current assets allocation?',f))

    def test_tiny_position_remains_bound(self):
        f=self.funds['motilal-nifty500']
        row=next(r for r in f['holdings'] if r['row']==510)
        self.assertEqual(row['weight_display'],'<0.005%')
        self.assertFalse(row['eligible'])

    def test_base_and_total_expenses_are_not_interchangeable(self):
        self.assertEqual(answer('What is the total TER?',self.funds['hdfc-defence']),REFUSAL)
        out=answer('What is the base expense ratio?',self.funds['motilal-nifty500'])
        self.assertIn('0.13%',out)
        self.assertNotIn('0.23%',out)

    def test_refusals_do_not_substitute_plan_date_or_report(self):
        f=self.funds['motilal-nifty500']
        for q in ['What is the Regular expense ratio?', 'September 2026 expense ratio?',
                  'What was the expense ratio in 2030?', 'What is today’s expense ratio?',
                  'Should I invest?', 'What is the best fund?', 'What is Reliance revenue?',
                  'What is its one year return?', 'What is the portfolio weight of XYZ?',
                  'What is the benchmark and forecast return?']:
            with self.subTest(q=q):self.assertEqual(answer(q,f),REFUSAL)
        self.assertNotEqual(answer('August 2026 Direct expense ratio?',f),REFUSAL)

    def test_exact_dates_must_match_the_selected_field(self):
        f=self.funds['hdfc-defence']
        for q in ['2026-08-30 benchmark?', '29 September 2026 benchmark?',
                  'September 29, 2026 benchmark?', '30/08/2026 benchmark?']:
            with self.subTest(q=q):self.assertEqual(answer(q,f),REFUSAL)
        for q in ['2026-09-30 benchmark?', '30 September 2026 benchmark?',
                  'September 30, 2026 benchmark?']:
            with self.subTest(q=q):self.assertNotEqual(answer(q,f),REFUSAL)
