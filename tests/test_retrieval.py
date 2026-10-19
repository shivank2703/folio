"""Regressions for source identity, continuation budgets and unit inheritance."""
import unittest
from ingest.preprocess import normalize_glyphs, is_unit_declaration
from ingest.scope import heading_scope
from ingest.quality import interleaved_prose
from ingest.chunk import chunk_page
from retrieve.search import FIELDS, fuse, page_context

class Rows:
    def __init__(self, rows): self.rows = rows
    def search(self): return self
    def where(self, expression):
        import re
        page = int(re.search(r'page = (\d+)', expression)[1])
        return Rows([r for r in self.rows if r['page'] == page])
    def limit(self, n): return self
    def select(self, fields): return self
    def to_list(self): return self.rows

def row(page, chunk, company='AAA'):
    return dict(company=company,fiscal_year='FY26',page=page,chunk=chunk,tokens=100,
                scope='standalone',text=f'page {page} row {chunk}',vector=[1.0],score=.9)

class RetrievalTests(unittest.TestCase):
    def test_rank_fusion_keeps_filing_identity(self):
        a,b=row(1,0),row(1,0,'BBB')
        self.assertEqual(len(fuse([[a,b],[b,a]])),2)

    def test_strong_page_continuation_survives_budget(self):
        rows=[row(10,i) for i in range(4)]+[row(20,i) for i in range(4)]
        context=page_context(Rows(rows),[rows[0],rows[4]],budget=500,seeds=2)
        self.assertEqual({(r['page'],r['chunk']) for r in context},
                         {(10,0),(10,1),(10,2),(10,3),(20,0)})
        self.assertLessEqual(sum(r['tokens'] for r in context),500)
        self.assertEqual(page_context(Rows(rows),[rows[0]],budget=50),[])

    def test_mixed_filings_rejected(self):
        with self.assertRaises(ValueError):page_context(Rows([]),[row(1,0),row(1,0,'BBB')])

    def test_scope_is_explicit_and_ambiguity_preserved(self):
        self.assertEqual(heading_scope('S T A N D A L O N E\nBalance Sheet'),'standalone')
        self.assertEqual(heading_scope('Consolidated financial statements\nNotes to accounts'),'consolidated')
        self.assertEqual(heading_scope('Standalone balance sheet\nConsolidated balance sheet'),'mixed')
        self.assertEqual(heading_scope('We improved consolidated revenue in the year.'),'unstated')

    def test_units_survive_later_chunks(self):
        for original in ['(All amounts are in Rs. Lakhs, except otherwise stated)',
                         '(C in ‘000)','H in Millions','v crore','(I crore)','Rupees crores','(000s omitted)']:
            unit=normalize_glyphs(original)
            with self.subTest(unit=unit):
                self.assertTrue(is_unit_declaration(unit))
                page={'text':unit+'\n'+'\n'.join(f'Financial row {i} | 1,234.56 | 7,890.12' for i in range(40)),
                      'units':[unit],'headers':[],'title':None}
                chunks=chunk_page(page)
                self.assertGreater(len(chunks),1)
                self.assertTrue(all(unit in c for c in chunks))
        self.assertFalse(is_unit_declaration('The company earned Rs 400 crores.'))
        self.assertEqual(normalize_glyphs('C in the company name'),'C in the company name')

    def test_interleaved_prose_is_not_numeric_table(self):
        self.assertTrue(interleaved_prose('\n'.join(['We manufacture products for customers | The board approved the transaction']*8)))
        self.assertFalse(interleaved_prose('\n'.join(['Total assets at the year end | 123.45 | 98.76']*20)))

class QueryTests(unittest.TestCase):
    def test_keyword_query_keeps_the_requested_account_label(self):
        from retrieve.search import keyword_query, without_company
        self.assertEqual(keyword_query('What were BEL standalone total assets at the end of FY26?', 'BEL'), 'total assets')
        self.assertNotIn('INDO-MIM', without_company('INDO-MIM total assets', 'INDOMIM'))
        self.assertIn('assets', without_company('BEL assets', None))

    def test_dot_leaders_do_not_hide_financial_values(self):
        from ingest.chunk import chunk_page
        page={'text':'Stores consumed' + '.'*500 + ' | 689.42 | 540.88', 'title':None,'headers':[],'units':[]}
        chunks=chunk_page(page)
        self.assertIn('689.42 | 540.88',chunks[0])
        self.assertNotIn('....',chunks[0])
